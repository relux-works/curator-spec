// Command generate-hardened creates the Curator hardened execution profile
// conformance suite. It is deliberately separate from generate-vectors: the
// portable candidate suite under conformance/v1 is accepted and pinned, and
// this command must never write into it.
package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"hash"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

const (
	// hardenedProfileVersion is the candidate identity of this suite. It is
	// separate from the portable protocol candidate version on purpose.
	hardenedProfileVersion = "hardened-1.0.0-rc.1"
	// portableProtocolVersion is the accepted portable candidate this profile
	// is additive to. Not one of its bytes changes here.
	portableProtocolVersion = "1.0.0-rc.5"
	// hardenedProfileIdentity names the complete guarantee set, capability
	// inventory, ordering, and diagnostics of this revision.
	hardenedProfileIdentity = "hardened-profile-v1"
	// hardenedExecutionPolicy is the identity protocol/core.md section 4.2.1
	// reserved for this profile.
	hardenedExecutionPolicy = "hardened-worker-v1"
	// portableExecutionPolicy is the single execution policy protocol 1.0
	// defines. It stays closed and unchanged.
	portableExecutionPolicy = "manager-worker-v1"
	// identityBindingVersion names the model that binds the profile identity
	// and the concrete trusted computing base into every reusable output.
	identityBindingVersion = "hardened-identity-binding-v1"
	// tcbDigestAlgorithm is the domain-separated, length-framed digest of the
	// closed hardened-tcb-v1 record. Its value is what the hashed build input
	// carries, so cache reuse cannot cross a trusted computing base.
	tcbDigestAlgorithm = "curator-hardened-tcb-v1"
	// capabilityInventoryVersion names the exhaustive hardened capability
	// class inventory.
	capabilityInventoryVersion = "hardened-capability-inventory-v1"
	// evidenceRecordVersion names the closed per-operation hardened reporting
	// record. It is distinct from the portable capability-evidence-v1 record.
	evidenceRecordVersion = "hardened-capability-evidence-v1"
	// tcbRecordVersion names the closed trusted-computing-base record.
	tcbRecordVersion = "hardened-tcb-v1"
	// componentFileAlgorithm and componentTreeAlgorithm are the two
	// domain-separated, length-framed trusted-component digest constructions
	// protocol/hardened-execution.md section 2.3.1 defines.
	componentFileAlgorithm = "curator-hardened-component-file-v1"
	componentTreeAlgorithm = "curator-hardened-component-tree-v1"
	// componentFixtureVersion names the published fixture set a reader uses to
	// recompute every trusted-component digest in this suite independently.
	componentFixtureVersion = "hardened-component-digest-fixtures-v1"
	// hostBuildAlgorithm is the domain-separated, length-framed kernel build
	// identity of section 2.3.3. review-cycle-4 finding R4-1: a nullable
	// descriptive build string let two materially different kernels reporting one
	// platform and one release produce one trusted-computing-base record.
	hostBuildAlgorithm = "curator-hardened-host-build-v1"
	// hostBuildFixtureVersion names the published fixture set a reader uses to
	// recompute every kernel build identity in this suite independently.
	hostBuildFixtureVersion = "hardened-host-build-fixtures-v1"
	// backendVersionGrammar names the comparable enforcement-backend version
	// identity of section 2.3.4. A claim's minimum_version uses it too, so
	// qualification is a comparison rather than a string match.
	backendVersionGrammar = "hardened-backend-version-v1"
	// ownerStory owns the hardened profile.
	ownerStory = "STORY-260728-327soo"
	// specifyingTask owns this specification.
	specifyingTask = "TASK-260728-1jafds"
	// verificationTask independently verifies the hardened profile.
	verificationTask = "TASK-260728-1itx7a"
	// sourceBaselineCommit is the committed baseline both candidates sit on.
	sourceBaselineCommit = "57c1f56846d221ecc55786bd3c2467ec32f11730"
	// createdAt is fixed so the suite regenerates byte-identically.
	createdAt = "2026-07-28T00:00:00Z"
	// reservedPolicySlotCacheKey is the key conformance/v1 recorded for an
	// input that carries only the reserved hardened execution-policy value in
	// the portable policy slot. rc.5 marks that input schema_valid: false, and
	// it is not a hardened build input: a hardened input additionally binds the
	// profile identity and the trusted-computing-base digest. The hardened
	// suite therefore keeps this key as a fourth non-aliasing comparison point
	// rather than reproducing it.
	reservedPolicySlotCacheKey = "sha256:13736230d33ce59de7f7323dcd4cffd510655ad8dabd5ee9e8b6cb182ec70037"
	// portableCacheKey and legacyRC4CacheKey are the two keys the same source
	// produces under the portable policy and under the pre-revision input.
	portableCacheKey  = "sha256:529370122ae11e2e961d5265b1a020e046bcd43165b2eb96b05e73a51187ac9b"
	legacyRC4CacheKey = "sha256:3fcd714a40e8918eb67dbd35d435875dcce6c9047da811a1fa26626e5e57be48"

	fixedCommit    = "0123456789abcdef0123456789abcdef01234567"
	buildSourceSHA = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
	toolchainSHA   = "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
	artifactSHA    = "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
	supervisorSHA  = "sha256:eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
	workerSHA      = "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
	externalSHA    = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	// parentSHA is the installed manager parent. protocol/hardened-execution.md
	// section 3.4 trusts it, so hardened-tcb-v1 names it: a manager parent that
	// launches a different supervisor is a different trusted computing base.
	parentSHA = "sha256:2222222222222222222222222222222222222222222222222222222222222222"
	// The rotated values. Each one isolates exactly one bound identity. Trusted
	// component digests are deliberately absent here: every one of them comes
	// from a published fixture instead, so no component identity is invented.
	updatedWorkerSHA     = "sha256:1111111111111111111111111111111111111111111111111111111111111111"
	updatedParentSHA     = "sha256:6666666666666666666666666666666666666666666666666666666666666666"
	updatedSupervisorSHA = "sha256:7777777777777777777777777777777777777777777777777777777777777777"
	updatedToolchainSHA  = "sha256:9999999999999999999999999999999999999999999999999999999999999999"
)

// guaranteeNames are the six deferred guarantees named by protocol/core.md
// section 4.2.1, in the sorted order the schemas use.
var guaranteeNames = []string{
	"exact-executable-allowlisting",
	"fail-closed-capability-preflight",
	"hard-aggregate-descendant-resource-bounds",
	"private-build-root-only-writes",
	"read-only-source-and-toolchain",
	"total-network-denial",
}

// capabilityClasses is the exhaustive hardened-capability-inventory-v1 set.
var capabilityClasses = []string{
	"active-capability-probe",
	"aggregate-resource-bounds",
	"domain-atomic-termination",
	"domain-membership-enforcement",
	"exec-path-allowlist",
	"filesystem-view-restriction",
	"network-syscall-denial",
	"preexisting-endpoint-revocation",
	"read-only-source-view",
	"read-only-toolchain-view",
	"write-path-confinement",
}

// guaranteeClasses maps each guarantee onto the classes that must all be
// available and applied before it may be reported as established.
var guaranteeClasses = map[string][]string{
	"exact-executable-allowlisting":             {"domain-membership-enforcement", "exec-path-allowlist"},
	"fail-closed-capability-preflight":          {"active-capability-probe"},
	"hard-aggregate-descendant-resource-bounds": {"aggregate-resource-bounds", "domain-atomic-termination", "domain-membership-enforcement"},
	"private-build-root-only-writes":            {"domain-membership-enforcement", "filesystem-view-restriction", "write-path-confinement"},
	"read-only-source-and-toolchain":            {"filesystem-view-restriction", "read-only-source-view", "read-only-toolchain-view"},
	"total-network-denial":                      {"domain-membership-enforcement", "network-syscall-denial", "preexisting-endpoint-revocation"},
}

func main() {
	root := flag.String("root", ".", "specification repository root")
	flag.Parse()
	suite := filepath.Join(*root, "conformance", "hardened", "v1")
	vectors := filepath.Join(suite, "vectors")
	must(os.MkdirAll(vectors, 0o755))

	writeProfileVector(vectors)
	writeAdversarialVector(vectors)
	writeIdentitySeparationVector(vectors)
	writeSchemaCases(suite)
	writeManifest(suite)
	writeReleaseMetadata(*root, suite)
}

// -----------------------------------------------------------------------
// vectors/hardened-execution-profile.json
// -----------------------------------------------------------------------

func writeProfileVector(dir string) {
	writeJSON(filepath.Join(dir, "hardened-execution-profile.json"), map[string]any{
		"schema_version":              1,
		"profile_version":             hardenedProfileVersion,
		"hardened_profile":            hardenedProfileIdentity,
		"execution_policy":            hardenedExecutionPolicy,
		"identity_binding_version":    identityBindingVersion,
		"portable_execution_policy":   portableExecutionPolicy,
		"portable_protocol_version":   portableProtocolVersion,
		"portable_suite_root":         "conformance/v1",
		"portable_suite_modified":     false,
		"owner_story":                 ownerStory,
		"specifying_task":             specifyingTask,
		"verification_task":           verificationTask,
		"drivers":                     []any{"go-repository-v1", "go-v1"},
		"partial_profile_permitted":   false,
		"portable_fallback_permitted": false,
		"process_graph":               processGraph(),
		"domain_session_states":       domainSessionStates(),
		"guarantees":                  guarantees(),
		"capability_inventory":        capabilityInventory(),
		"platform_declarations":       platformDeclarations(),
		"phase_list_authority":        phaseListAuthority(),
		"ordered_phases":              orderedPhases(),
		"ordering_invariants":         orderingInvariants(),
		"in_domain_self_test":         inDomainSelfTest(),
		"identity_reverification":     identityReverification(),
		"failure_boundary":            failureBoundary(),
		"capability_evidence_record":  evidenceRecordShape(),
		"diagnostics":                 diagnostics(),
		"package_influence_exclusions": []any{
			"argument vector, environment value, working directory, build tag, or flag",
			"artifact verifier, artifact path, cache key, receipt, marker, claim, or publication step",
			"build domain, its membership, its lifetime, or its teardown",
			"capability probe, capability class, guarantee, self-test, or evidence record",
			"enforcement backend selection",
			"go or GOROOT tool executable path",
			"hardened profile selection, profile identity, or execution-policy identity",
			"hook, plugin, generator, post-build action, or fallback",
			"network policy, trust root, key, pin, allowlist, or certificate",
			"resource bound or deadline",
			"session channel, session nonce, session message, or build permit",
			"source, toolchain, or write view, private root, permitted path, or executable allowlist",
			"supervisor or worker executable, hidden mode, or identity",
		},
	})
}

// phasesFor returns the ordered phase names a graph node performs, so the
// process graph and the ordered phase list cannot drift apart.
func phasesFor(node string) []any {
	out := []any{}
	for _, spec := range phaseSpecs() {
		if spec.actor == node {
			out = append(out, spec.name)
		}
	}
	return out
}

func processGraph() []any {
	return []any{
		map[string]any{
			"node": "manager-parent", "in_build_domain": false, "trusted": true,
			"selected_by": "manager", "package_selectable": false,
			"role":            "owns policy, identity, cache lookup, graph validation, build permit, artifact verification, and publication",
			"performs_phases": phasesFor("manager-parent"),
		},
		map[string]any{
			"node": "hardened-supervisor", "in_build_domain": false, "trusted": true,
			"selected_by": "manager", "package_selectable": false,
			"role":            "probes capabilities, creates the build domain, applies every control, launches the domain-root worker into it, and destroys it",
			"performs_phases": phasesFor("hardened-supervisor"),
		},
		map[string]any{
			"node": "domain-root-worker", "in_build_domain": true, "trusted": true,
			"selected_by": "manager", "package_selectable": false,
			"role":            "first process inside the domain; self-tests the guarantees from inside before any package byte, then runs exactly one go list and one go build",
			"performs_phases": phasesFor(inDomainActor),
		},
		map[string]any{
			"node": "go-launcher", "in_build_domain": true, "trusted": true,
			"selected_by": "manager", "package_selectable": false,
			"role":            "fingerprinted <GOROOT>/bin/go",
			"performs_phases": []any{},
		},
		map[string]any{
			"node": "goroot-tools", "in_build_domain": true, "trusted": true,
			"selected_by": "manager", "package_selectable": false,
			"role":            "fingerprinted regular executables below <GOROOT>/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/",
			"performs_phases": []any{},
		},
	}
}

func domainSessionStates() []any {
	return []any{
		"domain-created", "controls-applied", "domain-entered",
		"worker-identity-proved", "nonce-acknowledged", "self-test-passed",
		"evidence-emitted", "list-running", "list-returned", "graph-validated",
		"permit-issued", "build-running", "build-returned", "artifact-verified",
		"identities-reverified", "domain-torn-down",
	}
}

type guaranteeSpec struct {
	name            string
	requirement     string
	notSufficient   []string
	portableStopsAt string
}

func guaranteeSpecs() []guaranteeSpec {
	return []guaranteeSpec{
		{
			name:        "exact-executable-allowlisting",
			requirement: "the kernel denies execution of every path outside the exact fingerprinted allowlist, for every process in the build domain, including a file the domain just wrote",
			notSufficient: []string{
				"an empty PATH",
				"a manager promise to start nothing else",
				"a noexec mount over only part of the reachable filesystem",
				"identity verification of the programs the manager itself starts",
			},
			portableStopsAt: "fixed-manager-selected-graph-with-identity-verification",
		},
		{
			name:        "fail-closed-capability-preflight",
			requirement: "every capability class is actively probed on this host in this operation before domain entry, and any failed, inconclusive, or unprobed class rejects before domain entry with nothing published",
			notSufficient: []string{
				"a build-time constant",
				"a cached result from an earlier operation",
				"a configuration file",
				"a host label",
				"an operating-system version comparison alone",
				"a probe of a subset of the classes",
				"a probe performed after domain entry",
			},
			portableStopsAt: "mandatory-control-preflight-only",
		},
		{
			name:        "hard-aggregate-descendant-resource-bounds",
			requirement: "wall-clock, CPU, memory, process and thread count, descriptor, private-build-root byte, and combined-output bounds hold over the whole domain in aggregate; the host or the supervisor accounts for each, no domain member can evade the accounting or prevent the enforcement, and exceeding any bound destroys the entire domain",
			notSufficient: []string{
				"a bound over a process group or session a contained process can leave",
				"a parent-side deadline a descendant can outlive by detaching",
				"a parent-side deadline that kills only the direct child",
				"a per-process resource limit",
				"a periodic sweep for stray processes",
				"an accounting-only control with no enforcement",
			},
			portableStopsAt: "parent-enforced-deadline-output-and-artifact-bounds",
		},
		{
			name:        "private-build-root-only-writes",
			requirement: "the kernel denies every mutating filesystem operation by every process in the build domain outside the operation-private build root, and paths outside the declared views are unreachable",
			notSufficient: []string{
				"a manager promise to write only to private roots",
				"a post-hoc scan for unexpected files",
				"a private temporary directory the domain can escape by absolute path",
				"a TMPDIR value",
			},
			portableStopsAt: "manager-private-roots-and-verified-artifact",
		},
		{
			name:        "read-only-source-and-toolchain",
			requirement: "the frozen source snapshot and the fingerprinted GOROOT are presented through views the kernel refuses to mutate, regardless of the contained process's own credentials",
			notSufficient: []string{
				"a copy the manager promises not to write to",
				"filesystem permissions or an access-control list the domain can change",
				"re-verifying the snapshot digest after the fact",
			},
			portableStopsAt: "frozen-snapshot-with-identity-reverification",
		},
		{
			name:        "total-network-denial",
			requirement: "the kernel denies every network operation on every address family for every process in the build domain, and no inherited or pre-connected endpoint survives domain entry",
			notSufficient: []string{
				"GOPROXY=off, GOVCS=*:off, GOFLAGS, or vendor-only module mode",
				"a DNS blackhole or a userspace resolver stub",
				"a firewall rule the domain can change",
				"a post-hoc check that no connection was observed",
				"an empty PATH or an unset proxy environment",
			},
			portableStopsAt: "none",
		},
	}
}

func guarantees() []any {
	out := make([]any, 0, len(guaranteeSpecs()))
	for _, spec := range guaranteeSpecs() {
		out = append(out, map[string]any{
			"name":                         spec.name,
			"requirement":                  spec.requirement,
			"kernel_or_hypervisor":         true,
			"deferred_by_portable":         true,
			"portable_mechanism_stops_at":  spec.portableStopsAt,
			"not_sufficient":               stringsToAny(spec.notSufficient),
			"required_capability_classes":  stringsToAny(guaranteeClasses[spec.name]),
			"claimable_under_portable":     false,
			"established_in_this_revision": false,
		})
	}
	return out
}

func capabilityInventory() map[string]any {
	requirements := map[string]string{
		"active-capability-probe":         "every class above is actively probed on this host in this operation before domain entry",
		"aggregate-resource-bounds":       "the host accounts for and enforces every bound of the resource guarantee over the domain in aggregate",
		"domain-atomic-termination":       "the whole domain is destroyed as one unit, with no survivor and no reparenting",
		"domain-membership-enforcement":   "every descendant of the domain-root worker is a domain member and cannot renounce membership",
		"exec-path-allowlist":             "execution is denied for every path outside the exact fingerprinted allowlist",
		"filesystem-view-restriction":     "paths outside the declared views are unreachable from inside the domain",
		"network-syscall-denial":          "the kernel denies every network operation on every address family for every domain member",
		"preexisting-endpoint-revocation": "no inherited socket, handle, or connected endpoint is usable after domain entry",
		"read-only-source-view":           "the frozen source snapshot is presented through a kernel-enforced read-only view",
		"read-only-toolchain-view":        "the fingerprinted GOROOT is presented through a kernel-enforced read-only view",
		"write-path-confinement":          "every mutating filesystem operation outside the private build root is denied by the kernel",
	}
	classes := make([]any, 0, len(capabilityClasses))
	for _, name := range capabilityClasses {
		serves := make([]string, 0, 2)
		for guarantee, required := range guaranteeClasses {
			for _, class := range required {
				if class == name {
					serves = append(serves, guarantee)
				}
			}
		}
		sort.Strings(serves)
		classes = append(classes, map[string]any{
			"name":        name,
			"requirement": requirements[name],
			"serves":      stringsToAny(serves),
			"optional":    false,
		})
	}
	return map[string]any{
		"version":             capabilityInventoryVersion,
		"exhaustive":          true,
		"probe_scope":         "per-operation",
		"probe_timing":        "pre-domain-entry",
		"availability_states": []any{"available", "unavailable", "unprobed"},
		"status_states":       []any{"applied", "not-applied"},
		"not_a_probe": []any{
			"a build-time constant",
			"a cached result from an earlier operation",
			"a configuration file",
			"a host label",
			"an operating-system version comparison alone",
		},
		"classes":   classes,
		"authority": "conformance/hardened/v1/vectors/hardened-execution-profile.json#capability_inventory",
	}
}

func platformDeclarations() []any {
	return []any{
		map[string]any{
			"platform":             "linux",
			"enforcement_backend":  "linux-namespace-seccomp-v1",
			"qualification_status": "unqualified",
			"qualification_tasks":  []any{"TASK-260728-3ihgfq", "TASK-260728-ns5yk7"},
			"native_evidence":      "absent",
			"candidate_primitives": []any{
				"a size-limited tmpfs or quota-backed subvolume for the aggregate write-byte bound",
				"cgroup v2 cgroup.kill for atomic domain termination",
				"cgroup v2 pids.max, memory.max, and CPU limits for aggregate bounds",
				"empty network namespace for network denial",
				"read-only bind mounts for the source and toolchain views",
				"seccomp-BPF with no_new_privs for execution allowlisting and residual syscall denial",
				"user, mount, PID, network, IPC, UTS, and cgroup namespaces for domain membership",
			},
			"blocking_capability_classes": []any{},
			"blocking_reason":             nil,
			"minimum_version":             nil,
			"required_configuration":      []any{},
		},
		map[string]any{
			"platform":             "macos",
			"enforcement_backend":  "macos-sandbox-v1",
			"qualification_status": "unqualified",
			"qualification_tasks":  []any{"TASK-260728-3n67j6", "TASK-260728-jis03f"},
			"native_evidence":      "absent",
			"candidate_primitives": []any{
				"(deny default) sandbox profile with explicit file-read* allowances",
				"(deny network*) for network denial",
				"(deny process-exec*) with exact-path allowances",
				"RLIMIT_* for per-process bounds",
				"file-write* restricted to the operation-private build root",
				"process group and session teardown",
			},
			"blocking_capability_classes": []any{"aggregate-resource-bounds", "domain-atomic-termination", "domain-membership-enforcement"},
			"blocking_reason":             "the platform exposes no unescapable per-operation process domain, so a contained process can leave the process group or session, and no aggregate private storage, memory, or process-count accounting exists; this is the same no-private-aggregate-domain finding the portable inventory records",
			"minimum_version":             nil,
			"required_configuration":      []any{},
		},
		map[string]any{
			"platform":             "windows",
			"enforcement_backend":  "windows-appcontainer-job-v1",
			"qualification_status": "unqualified",
			"qualification_tasks":  []any{"TASK-260728-1v71sx", "TASK-260728-2hcmtg"},
			"native_evidence":      "absent",
			"candidate_primitives": []any{
				"AppContainer or LPAC token with a per-operation package SID and no network capability SIDs",
				"Job Object ActiveProcessLimit, JobMemoryLimit, and JobTime for aggregate process, memory, and CPU bounds",
				"Job Object JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE for atomic termination",
				"PROC_THREAD_ATTRIBUTE_JOB_LIST and an explicit handle inheritance list",
				"access-control entries granting the package SID read-only snapshot and GOROOT access",
			},
			"blocking_capability_classes": []any{"aggregate-resource-bounds", "exec-path-allowlist"},
			"blocking_reason":             "child-process creation policy is all-or-none and exposes no supported per-path execution allowlist for a contained token, and no supported facility bounds the bytes a job writes below the private build root",
			"minimum_version":             nil,
			"required_configuration":      []any{},
		},
	}
}

// phaseSpec is one row of the single normative ordered phase list. The list is
// executable: every phase names the exact actor that performs it, and an actor
// that lives inside the build domain cannot appear before domain entry.
type phaseSpec struct {
	name              string
	actor             string
	diagnostic        any
	skippedOnCacheHit bool
}

// domainEntryPhase and firstPackagePhase are the two boundaries the whole
// profile is written around.
const (
	domainEntryPhase  = "domain-entry"
	firstPackagePhase = "go-list"
	inDomainActor     = "domain-root-worker"
)

func phaseSpecs() []phaseSpec {
	return []phaseSpec{
		{"profile-selection", "manager-parent", "hardened_profile_claim_forbidden", false},
		{"platform-qualification", "manager-parent", "hardened_profile_unsupported", false},
		{"capability-probe", "hardened-supervisor", "hardened_capability_unavailable", false},
		{"toolchain-probe-and-snapshot-freeze", "manager-parent", nil, false},
		{"tcb-identity-verification", "manager-parent", "hardened_tcb_identity_invalid", false},
		{"build-input-and-cache-lookup", "manager-parent", nil, false},
		{"domain-establishment", "hardened-supervisor", "hardened_domain_establishment_failed", true},
		{domainEntryPhase, "hardened-supervisor", "hardened_domain_establishment_failed", true},
		{"in-domain-guarantee-self-test", inDomainActor, "hardened_domain_establishment_failed", true},
		{firstPackagePhase, inDomainActor, "hardened_domain_breach_detected", true},
		{"parent-graph-validation", "manager-parent", nil, true},
		{"build-permit", "manager-parent", "hardened_domain_protocol_invalid", true},
		{"go-build", inDomainActor, "hardened_domain_breach_detected", true},
		{"artifact-verification", "manager-parent", nil, true},
		// review-cycle-4 finding R4-2: teardown joins the whole domain first, so
		// re-verification observes a state no domain member can still change.
		{"domain-teardown", "hardened-supervisor", "hardened_domain_breach_detected", true},
		{"identity-reverification", "manager-parent", "hardened_tcb_identity_invalid", true},
		{"publication", "manager-parent", nil, false},
	}
}

// phaseListAuthority names the one normative ordered phase list and every
// document that must mirror it without restating an order of its own.
func phaseListAuthority() map[string]any {
	return map[string]any{
		"normative_document": "protocol/hardened-execution.md",
		"normative_section":  "7.2",
		"executable_form":    "conformance/hardened/v1/vectors/hardened-execution-profile.json#ordered_phases",
		"mirrors": []any{
			"conformance/hardened/v1/vectors/hardened-execution-profile.json",
			"profiles/manager-hardened.md",
			"protocol/hardened-execution.md",
		},
		"independent_orderings_permitted": false,
		"domain_entry_phase":              domainEntryPhase,
		"first_package_exposure_phase":    firstPackagePhase,
		"in_domain_actor":                 inDomainActor,
	}
}

func phaseIndex(name string) int {
	for index, spec := range phaseSpecs() {
		if spec.name == name {
			return index
		}
	}
	panic("unknown hardened phase " + name)
}

func orderedPhases() []any {
	entry := phaseIndex(domainEntryPhase)
	exposure := phaseIndex(firstPackagePhase)
	out := make([]any, 0, len(phaseSpecs()))
	for index, spec := range phaseSpecs() {
		out = append(out, map[string]any{
			"index":                          index + 1,
			"name":                           spec.name,
			"actor":                          spec.actor,
			"actor_in_build_domain":          spec.actor == inDomainActor,
			"before_domain_entry":            index < entry,
			"before_package_exposure":        index < exposure,
			"package_bytes_reach_go_process": index >= exposure,
			"skipped_on_exact_cache_hit":     spec.skippedOnCacheHit,
			"rejection_diagnostic":           spec.diagnostic,
		})
	}
	return out
}

// orderingInvariants are the relations that make the phase list executable
// rather than merely enumerated. Each one is checked against ordered_phases.
func orderingInvariants() []any {
	pairs := []struct{ name, earlier, later, because string }{
		{
			"capability-probe-before-domain-establishment", "capability-probe", "domain-establishment",
			"a control cannot be applied before the host is known to provide it",
		},
		{
			"tcb-verification-before-cache-lookup", "tcb-identity-verification", "build-input-and-cache-lookup",
			"the cache key carries the trusted-computing-base digest, so the trusted computing base must be verified first",
		},
		{
			"cache-lookup-before-domain-establishment", "build-input-and-cache-lookup", "domain-establishment",
			"an exact verified hit compiles nothing, so it never creates a build domain",
		},
		{
			"domain-entry-before-in-domain-self-test", domainEntryPhase, "in-domain-guarantee-self-test",
			"the domain-root worker is the first process inside the domain, so nothing can test from inside before it exists",
		},
		{
			"self-test-before-package-exposure", "in-domain-guarantee-self-test", firstPackagePhase,
			"no package byte may reach a Go process until the kernel has been observed denying one representative operation per guarantee",
		},
		{
			"graph-validation-before-build-permit", "parent-graph-validation", "build-permit",
			"the permit is issued only after the parent has rejected every forbidden dependency, directive, and native input",
		},
		{
			"build-permit-before-go-build", "build-permit", "go-build",
			"the worker cannot proceed to a compiler on its own",
		},
		{
			"teardown-before-identity-reverification", "domain-teardown", "identity-reverification",
			"the whole domain is destroyed and joined first, so re-verification observes trusted state no domain member can still change",
		},
		{
			"identity-reverification-before-publication", "identity-reverification", "publication",
			"nothing is published under a trusted computing base that has not been proved byte-for-byte unchanged",
		},
		{
			"teardown-before-publication", "domain-teardown", "publication",
			"nothing is published while a domain member is alive",
		},
	}
	out := make([]any, 0, len(pairs))
	for _, item := range pairs {
		out = append(out, map[string]any{
			"name":    item.name,
			"earlier": item.earlier,
			"later":   item.later,
			"because": item.because,
		})
	}
	return out
}

// inDomainSelfTest names the actor, the position, and the failure behavior of
// the guarantee self-test. It is the piece that makes the pre-package state
// machine executable: an actor inside the domain exists only after entry.
func inDomainSelfTest() map[string]any {
	return map[string]any{
		"phase":                             "in-domain-guarantee-self-test",
		"actor":                             inDomainActor,
		"actor_in_build_domain":             true,
		"runs_after_phase":                  domainEntryPhase,
		"runs_before_phase":                 firstPackagePhase,
		"verified_by":                       "hardened-supervisor",
		"channel":                           "pre-opened domain session channel",
		"guarantees_probed":                 stringsToAny(guaranteeNames),
		"package_bytes_read_by_domain":      false,
		"go_process_started":                false,
		"source_view_opened_by_worker":      false,
		"on_failure_diagnostic":             "hardened_domain_establishment_failed",
		"on_failure_tears_domain_down":      true,
		"on_failure_partial_mode_permitted": false,
		"on_failure_published":              false,
		"unperformable_test_is_a_failure":   true,
	}
}

// reverifiedMembers is every mutable member of the closed trusted-computing-base
// record plus the frozen source snapshot. review-cycle-4 finding R4-2: the
// manager obligation re-verified four identities while phase 5 had hashed
// twelve, so a member could change during the operation with no end-of-operation
// check at all.
func reverifiedMembers() []string {
	constant := map[string]bool{"record_version": true, "hardened_profile": true, "execution_policy": true}
	out := []string{"source-snapshot"}
	for _, item := range tcbBoundFields() {
		field := item.(map[string]any)["field"].(string)
		if !constant[field] {
			out = append(out, field)
		}
	}
	sort.Strings(out)
	return out
}

// identityReverification is the executable form of the end-of-operation check.
// It runs after the whole domain has been destroyed and joined, and it
// recomputes the complete record rather than spot-checking a few binaries.
func identityReverification() map[string]any {
	return map[string]any{
		"phase":                                "identity-reverification",
		"actor":                                "manager-parent",
		"runs_after_phase":                     "domain-teardown",
		"runs_before_phase":                    "publication",
		"domain_joined_before_reverification":  true,
		"recomputes_complete_tcb_record":       true,
		"observes_canonical_pinned_identities": true,
		"comparison":                           "byte-identical-record-and-digest",
		"reverified_members":                   stringsToAny(reverifiedMembers()),
		"partial_reverification_permitted":     false,
		"restating_earlier_record_permitted":   false,
		"on_change_diagnostic":                 "hardened_tcb_identity_invalid",
		"published_on_change":                  false,
		"skipped_on_exact_cache_hit":           true,
	}
}

func boundaryCase(phase, diagnostic string, compilerStarted bool) map[string]any {
	index := phaseIndex(phase)
	return map[string]any{
		"rejects_build":           true,
		"fails_before":            phase,
		"before_domain_entry":     index < phaseIndex(domainEntryPhase),
		"before_package_exposure": index < phaseIndex(firstPackagePhase),
		"compiler_started":        compilerStarted,
		"published":               false,
		"expected_error":          diagnostic,
	}
}

func failureBoundary() map[string]any {
	return map[string]any{
		"unqualified_platform":              boundaryCase("platform-qualification", "hardened_profile_unsupported", false),
		"unavailable_capability_class":      boundaryCase("capability-probe", "hardened_capability_unavailable", false),
		"unprobed_capability_class":         boundaryCase("capability-probe", "hardened_capability_unavailable", false),
		"tcb_identity_failure":              boundaryCase("tcb-identity-verification", "hardened_tcb_identity_invalid", false),
		"domain_establishment_failure":      boundaryCase("domain-establishment", "hardened_domain_establishment_failed", false),
		"domain_entry_failure":              boundaryCase(domainEntryPhase, "hardened_domain_establishment_failed", false),
		"self_test_not_denied":              boundaryCase("in-domain-guarantee-self-test", "hardened_domain_establishment_failed", false),
		"portable_fallback_after_rejection": boundaryCase("profile-selection", "hardened_profile_claim_forbidden", false),
		"guarantee_violated_after_entry":    boundaryCase("publication", "hardened_domain_breach_detected", true),
	}
}

func evidenceRecordShape() map[string]any {
	return map[string]any{
		"record_version":                evidenceRecordVersion,
		"distinct_from_portable_record": "capability-evidence-v1",
		"result_only":                   true,
		"exposed_in":                    []any{"dry-run-plan", "install", "status"},
		"excluded_from":                 []any{"cache-key", "conformance-claim", "install-marker", "receipt"},
		"record_fields": []any{
			"capabilities", "diagnostic", "enforcement_backend", "execution_policy",
			"guarantees", "hardened_profile", "outcome", "platform",
			"qualification_status", "record_version", "rejected_before",
		},
		"capability_entry_fields": []any{"availability", "name", "probed_at", "status"},
		"guarantee_entry_fields":  []any{"established", "name"},
		"entry_cardinality": map[string]any{
			"capabilities": "exactly-one-per-capability-class",
			"guarantees":   "exactly-one-per-guarantee",
		},
		"probe_timings": []any{"pre-domain-entry"},
		"consistency_rules": []any{
			"a guarantee reported established requires every mapped capability class applied",
			"a missing, duplicated, extra, or unknown capability or guarantee entry is an error",
			"a portable capability-evidence-v1 record for a hardened operation is an error",
			"an availability value not obtained by a probe in this operation is an error",
			"an available capability must report applied",
			"an execution_policy other than hardened-worker-v1 is an error",
			"an unavailable or unprobed capability must not report applied",
			"an unknown record_version is an error",
			"outcome established requires every capability applied and every guarantee established",
			"outcome rejected requires both rejected_before and diagnostic",
		},
		"examples": map[string]any{
			"rejected_unqualified": evidenceRecord("linux", "linux-namespace-seccomp-v1", "unqualified", "rejected", "platform-qualification", "hardened_profile_unsupported", false),
			"established":          evidenceRecord("linux", "linux-namespace-seccomp-v1", "qualified", "established", nil, nil, true),
		},
	}
}

func evidenceRecord(platform, backend, qualification, outcome string, rejectedBefore, diagnostic any, established bool) map[string]any {
	availability := "unprobed"
	status := "not-applied"
	if established {
		availability = "available"
		status = "applied"
	}
	capabilities := make([]any, 0, len(capabilityClasses))
	for _, name := range capabilityClasses {
		capabilities = append(capabilities, map[string]any{
			"name": name, "availability": availability, "status": status,
			"probed_at": "pre-domain-entry",
		})
	}
	guaranteeEntries := make([]any, 0, len(guaranteeNames))
	for _, name := range guaranteeNames {
		guaranteeEntries = append(guaranteeEntries, map[string]any{"name": name, "established": established})
	}
	return map[string]any{
		"record_version":       evidenceRecordVersion,
		"hardened_profile":     hardenedProfileIdentity,
		"execution_policy":     hardenedExecutionPolicy,
		"platform":             platform,
		"enforcement_backend":  backend,
		"qualification_status": qualification,
		"outcome":              outcome,
		"rejected_before":      rejectedBefore,
		"diagnostic":           diagnostic,
		"capabilities":         capabilities,
		"guarantees":           guaranteeEntries,
	}
}

func diagnostics() []any {
	rows := []struct{ code, state, severity, meaning string }{
		{"hardened_capability_unavailable", "unsupported", "error", "A required capability class probe reported unavailable, inconclusive, or unprobed"},
		{"hardened_domain_breach_detected", "corrupt", "error", "A guarantee was violated during the operation, or a domain member survived teardown"},
		{"hardened_domain_establishment_failed", "blocked", "error", "The build domain could not be created, a control could not be applied, or a guarantee self-test did not observe the expected denial"},
		{"hardened_domain_protocol_invalid", "blocked", "error", "Domain session framing, nonce, ordering, size, message kind, or permit sequence is invalid"},
		{"hardened_evidence_invalid", "corrupt", "error", "The hardened capability-evidence record is inconsistent, incomplete, or contradicts the applied profile"},
		{"hardened_package_influence_forbidden", "unsupported", "error", "Package data attempted to influence the hardened boundary, controls, views, limits, permits, evidence, or publication"},
		{"hardened_profile_claim_forbidden", "unsupported", "error", "A hardened identity was claimed by an operation that did not establish the hardened domain, or hardened and portable identities were mixed"},
		{"hardened_profile_unsupported", "unsupported", "error", "The host platform, version, or configuration is not a qualified hardened platform"},
		{"hardened_tcb_identity_invalid", "blocked", "error", "A supervisor, worker, launcher, or tool identity, substitution, or replacement check failed"},
	}
	out := make([]any, 0, len(rows))
	for _, row := range rows {
		out = append(out, map[string]any{
			"code": row.code, "state": row.state, "severity": row.severity,
			"meaning": row.meaning, "phase": "execution",
			"portable_code": false,
		})
	}
	return out
}

// -----------------------------------------------------------------------
// vectors/hardened-adversarial-vectors.json
// -----------------------------------------------------------------------

func writeAdversarialVector(dir string) {
	writeJSON(filepath.Join(dir, "hardened-adversarial-vectors.json"), map[string]any{
		"schema_version":              1,
		"profile_version":             hardenedProfileVersion,
		"hardened_profile":            hardenedProfileIdentity,
		"execution_policy":            hardenedExecutionPolicy,
		"evidence_status":             "pending-native-validation",
		"qualified_platforms":         []any{},
		"escape_cases":                escapeCases(),
		"capability_preflight_cases":  preflightCases(),
		"package_influence_cases":     packageInfluenceCases(),
		"identity_and_protocol_cases": identityCases(),
		"reverification_cases":        reverificationCases(),
		"tcb_completeness_cases":      tcbCompletenessCases(),
		"evidence_cases":              evidenceCases(),
		"no_fallback_cases":           noFallbackCases(),
	})
}

func escapeCase(name, guarantee, attack string) map[string]any {
	return map[string]any{
		"name":                                  name,
		"guarantee":                             guarantee,
		"attack":                                attack,
		"attacker":                              "package source compiled inside the build domain",
		"expected_outcome":                      "denied-by-kernel",
		"expected_error_if_observed_succeeding": "hardened_domain_breach_detected",
		"compiler_started":                      true,
		"published":                             false,
		"native_evidence_required":              true,
		"evidence_status":                       "pending-native-validation",
	}
}

func escapeCases() []any {
	cases := []struct{ name, guarantee, attack string }{
		{"network-outbound-tcp", "total-network-denial", "a domain member opens a TCP socket and connects to a routable address"},
		{"network-loopback", "total-network-denial", "a domain member connects to a loopback address"},
		{"network-unix-domain", "total-network-denial", "a domain member connects to a unix-domain socket path outside the domain"},
		{"network-inherited-endpoint", "total-network-denial", "a domain member writes to a socket descriptor inherited across domain entry"},
		{"network-raw-and-alternate-family", "total-network-denial", "a domain member creates a raw, packet, netlink, or other alternate-family socket"},
		{"source-write", "read-only-source-and-toolchain", "a domain member writes to a file in the frozen source snapshot"},
		{"source-rename-unlink", "read-only-source-and-toolchain", "a domain member renames or unlinks a file in the frozen source snapshot"},
		{"source-permission-change", "read-only-source-and-toolchain", "a domain member changes permissions, ownership, or extended attributes in the snapshot"},
		{"toolchain-write", "read-only-source-and-toolchain", "a domain member writes to a file below the fingerprinted GOROOT"},
		{"toolchain-hard-link", "read-only-source-and-toolchain", "a domain member creates a hard link to a GOROOT tool executable"},
		{"write-absolute-path-escape", "private-build-root-only-writes", "a domain member writes to an absolute path outside the private build root"},
		{"write-relative-traversal", "private-build-root-only-writes", "a domain member writes through a relative traversal out of the private build root"},
		{"write-symlink-escape", "private-build-root-only-writes", "a domain member writes through a symbolic link that resolves outside the private build root"},
		{"write-shared-temp", "private-build-root-only-writes", "a domain member writes into a shared system temporary directory"},
		{"write-device-or-ipc-object", "private-build-root-only-writes", "a domain member creates a device node or filesystem IPC object outside the private build root"},
		{"resource-process-flood", "hard-aggregate-descendant-resource-bounds", "a domain member forks until the aggregate process bound is exceeded"},
		{"resource-memory-flood", "hard-aggregate-descendant-resource-bounds", "domain members together allocate past the aggregate memory bound"},
		{"resource-disk-flood", "hard-aggregate-descendant-resource-bounds", "domain members together write past the aggregate private-build-root byte bound"},
		{"resource-output-flood", "hard-aggregate-descendant-resource-bounds", "domain members together emit past the aggregate combined-output bound"},
		{"resource-wall-clock-overrun", "hard-aggregate-descendant-resource-bounds", "domain members together run past the aggregate wall-clock deadline"},
		{"resource-detached-survivor", "hard-aggregate-descendant-resource-bounds", "a domain member detaches or reparents a process and attempts to outlive the domain"},
		{"exec-shell", "exact-executable-allowlisting", "a domain member executes a system shell"},
		{"exec-interpreter", "exact-executable-allowlisting", "a domain member executes a scripting interpreter"},
		{"exec-host-binary", "exact-executable-allowlisting", "a domain member executes an arbitrary host binary outside GOROOT"},
		{"exec-self-written-file", "exact-executable-allowlisting", "a domain member executes a file it just wrote into the private build root"},
		{"exec-dynamic-loader", "exact-executable-allowlisting", "a domain member invokes the dynamic loader as a program to run a non-allowlisted image"},
	}
	out := make([]any, 0, len(cases))
	for _, item := range cases {
		out = append(out, escapeCase(item.name, item.guarantee, item.attack))
	}
	return out
}

func preflightCases() []any {
	out := make([]any, 0, len(capabilityClasses)+2)
	for _, class := range capabilityClasses {
		out = append(out, map[string]any{
			"name":                   "unavailable-" + class,
			"forced_unavailable":     class,
			"availability":           "unavailable",
			"expected_error":         "hardened_capability_unavailable",
			"fails_before":           "capability-probe",
			"before_domain_entry":    true,
			"domain_created":         false,
			"compiler_started":       false,
			"published":              false,
			"falls_back_to_portable": false,
		})
	}
	out = append(out,
		map[string]any{
			"name":                   "unprobed-capability-class",
			"forced_unavailable":     nil,
			"availability":           "unprobed",
			"expected_error":         "hardened_capability_unavailable",
			"fails_before":           "capability-probe",
			"before_domain_entry":    true,
			"domain_created":         false,
			"compiler_started":       false,
			"published":              false,
			"falls_back_to_portable": false,
		},
		map[string]any{
			"name":                   "unqualified-platform",
			"forced_unavailable":     nil,
			"availability":           "unprobed",
			"expected_error":         "hardened_profile_unsupported",
			"fails_before":           "platform-qualification",
			"before_domain_entry":    true,
			"domain_created":         false,
			"compiler_started":       false,
			"published":              false,
			"falls_back_to_portable": false,
		},
	)
	return out
}

func packageInfluenceCases() []any {
	surfaces := []struct{ name, surface string }{
		{"package-selected-supervisor", "hardened supervisor executable or hidden mode"},
		{"package-selected-worker", "domain-root worker executable or hidden mode"},
		{"package-selected-enforcement-backend", "enforcement backend selection"},
		{"package-selected-executable-allowlist", "executable allowlist entries"},
		{"package-selected-view-path", "source, toolchain, or write view path"},
		{"package-selected-private-root", "operation-private root resolution"},
		{"package-selected-argv", "Go argument vector"},
		{"package-selected-environment", "build environment value"},
		{"package-selected-network-policy", "network policy or trust root"},
		{"package-selected-resource-bound", "aggregate resource bound or deadline"},
		{"package-selected-permit", "session channel, nonce, message, or build permit"},
		{"package-selected-hook", "hook, plugin, generator, or post-build action"},
		{"package-selected-evidence", "capability probe result or evidence record"},
		{"package-selected-profile", "hardened profile selection or profile identity"},
		{"package-selected-publication", "cache key, receipt, marker, claim, or publication step"},
	}
	out := make([]any, 0, len(surfaces))
	for _, item := range surfaces {
		out = append(out, map[string]any{
			"name":                item.name,
			"surface":             item.surface,
			"manifest_field":      nil,
			"descriptor_field":    nil,
			"expected_error":      "hardened_package_influence_forbidden",
			"before_domain_entry": true,
			"domain_created":      false,
			"compiler_started":    false,
			"published":           false,
		})
	}
	return out
}

func identityCases() []any {
	cases := []struct {
		name, expected string
		beforeEntry    bool
		compiler       bool
	}{
		{"supervisor-identity-mismatch", "hardened_tcb_identity_invalid", true, false},
		{"supervisor-replacement-race", "hardened_tcb_identity_invalid", true, false},
		{"worker-identity-mismatch", "hardened_tcb_identity_invalid", true, false},
		{"worker-symlink-substitution", "hardened_tcb_identity_invalid", true, false},
		{"worker-hard-link-substitution", "hardened_tcb_identity_invalid", true, false},
		{"go-launcher-identity-mismatch", "hardened_tcb_identity_invalid", true, false},
		{"goroot-tool-identity-mismatch", "hardened_tcb_identity_invalid", true, false},
		{"post-build-snapshot-identity-change", "hardened_tcb_identity_invalid", false, true},
		{"post-build-toolchain-identity-change", "hardened_tcb_identity_invalid", false, true},
		{"missing-session-nonce", "hardened_domain_protocol_invalid", false, false},
		{"replayed-session-nonce", "hardened_domain_protocol_invalid", false, false},
		{"second-list-request", "hardened_domain_protocol_invalid", false, false},
		{"build-before-permit", "hardened_domain_protocol_invalid", false, false},
		{"duplicate-build-permit", "hardened_domain_protocol_invalid", false, false},
		{"oversized-session-message", "hardened_domain_protocol_invalid", false, false},
		{"unknown-session-message-kind", "hardened_domain_protocol_invalid", false, false},
		{"surviving-domain-member-at-teardown", "hardened_domain_breach_detected", false, true},
	}
	out := make([]any, 0, len(cases))
	for _, item := range cases {
		out = append(out, map[string]any{
			"name":                item.name,
			"expected_error":      item.expected,
			"before_domain_entry": item.beforeEntry,
			"compiler_started":    item.compiler,
			"published":           false,
		})
	}
	return out
}

// reverificationCases is the adversarial face of the end-of-operation check.
// review-cycle-4 finding R4-2: an ordering that re-verified before the domain
// was joined, and a manager obligation that rechecked four of twelve members,
// were both locked in by the vector rather than detected by it. Every member the
// profile re-verifies now has an omission case of its own.
func reverificationCases() []any {
	out := []any{}
	add := func(name, kind string, member any, statement string) {
		out = append(out, map[string]any{
			"name":                name,
			"kind":                kind,
			"omitted_member":      member,
			"statement":           statement,
			"expected_error":      "hardened_tcb_identity_invalid",
			"detected":            true,
			"published":           false,
			"cache_entry_written": false,
			"marker_updated":      false,
		})
	}
	for _, member := range reverifiedMembers() {
		add(
			"reverification-omits-"+strings.ReplaceAll(member, "_", "-"),
			"omitted-member", member,
			"an end-of-operation check that re-verifies every other member but not "+member+
				", so that member can change during the operation while publication still attributes the artifact to the initial digest",
		)
	}
	add("reverification-before-domain-teardown", "phase-order", nil,
		"an implementation that re-verifies while the domain has not been destroyed and joined, so a surviving member can still change a trusted component afterwards")
	add("reverification-restates-the-initial-record", "restated-record", nil,
		"an implementation that compares the phase-5 record against itself, or its digest against itself, instead of observing every identity again")
	add("reverification-accepts-a-changed-component-after-artifact-verification", "changed-member", nil,
		"a trusted component replaced between artifact verification and the end of the operation, which the recomputed record MUST NOT reproduce")
	return out
}

// tcbCompletenessCases is the adversarial face of hardened-tcb-v1. For every
// member of the closed record there is an omission case, and for every relation
// there is a mismatch case. Each one must be rejected by a receipt reader, a
// marker reader, and a claim reader alike, before any reusable state is
// adopted.
func tcbCompletenessCases() []any {
	out := []any{}
	completeness := func(name, field, kind, rejectedBy, statement string) map[string]any {
		return map[string]any{
			"name":               name,
			"field":              field,
			"kind":               kind,
			"statement":          statement,
			"rejected_by":        rejectedBy,
			"expected_error":     "hardened_tcb_identity_invalid",
			"receipt_rejected":   true,
			"marker_rejected":    true,
			"claim_rejected":     true,
			"cache_entry_reused": false,
			"published":          false,
		}
	}
	for _, item := range tcbBoundFields() {
		field := item.(map[string]any)["field"].(string)
		out = append(out, completeness(
			"omit-"+strings.ReplaceAll(field, "_", "-"), field, "omission", "schema",
			"a trusted computing base that does not name "+field+" is not the concrete base the operation ran on",
		))
	}
	out = append(out,
		completeness("mismatch-platform-and-backend", "enforcement_backend", "relation-mismatch", "schema",
			"a platform paired with a backend another platform declares"),
		completeness("mismatch-target-and-platform", "platform", "relation-mismatch", "schema",
			"a receipt whose native target contradicts its own TCB platform"),
		completeness("mismatch-claim-operating-system-and-backend", "enforcement_backend", "relation-mismatch", "schema",
			"a claim entry pairing an operating system with a backend another operating system declares"),
		completeness("untyped-trusted-component", "trusted_components", "uncryptographic-component", "schema",
			"a trusted component named by an unconstrained string instead of a closed cryptographic record"),
		completeness("trusted-component-without-digest", "trusted_components", "uncryptographic-component", "schema",
			"a trusted component record that carries no content digest"),
		completeness("undeclared-mutable-component", "trusted_components", "narrower-than-trusted", "implementation",
			"an implementation that starts a mutable interpreter or installed package tree it does not name"),
		completeness("claim-tcb-names-an-unclaimed-operating-system", "platform", "relation-mismatch", "conformance-validator",
			"a claim whose trusted computing base names an operating system the claim itself does not declare"),
		completeness("claim-required-configuration-not-observed", "backend", "relation-mismatch", "conformance-validator",
			"a claim that requires a configuration setting its own trusted computing base did not observe"),
		completeness("lying-tcb-digest", "record_version", "digest-mismatch", "conformance-validator",
			"a hashed build input whose TCB digest is not the digest of the receipt's own record"),
		// review-cycle-3 finding R3-2.
		completeness("mismatch-host-identity-and-platform", "host", "relation-mismatch", "schema",
			"a trusted computing base that reports one platform and another platform's canonical kernel identity"),
		completeness("host-kind-outside-this-revision", "host", "relation-mismatch", "schema",
			"a trusted computing base that reports a hypervisor host, which no backend this revision declares can supply"),
		completeness("mismatch-backend-version-series", "backend", "relation-mismatch", "schema",
			"a trusted computing base whose observed backend version carries another backend's series token"),
		completeness("malformed-backend-version", "backend", "relation-mismatch", "schema",
			"a trusted computing base whose observed backend version is outside the hardened-backend-version-v1 grammar"),
		completeness("claim-backend-version-below-minimum", "backend", "relation-mismatch", "conformance-validator",
			"a claim whose own trusted computing base observes a backend version below the minimum that claim declares"),
		// review-cycle-3 finding R3-1.
		completeness("mismatch-component-algorithm-and-kind", "trusted_components", "relation-mismatch", "schema",
			"a trusted component whose digest algorithm is one its kind does not admit"),
		completeness("component-digest-not-reproducible-from-bytes", "trusted_components", "uncryptographic-component", "implementation",
			"a component digest that the published fixture bytes and the section 2.3.1 construction do not reproduce"),
		completeness("component-link-substituted-for-file", "trusted_components", "uncryptographic-component", "implementation",
			"a tree component whose symbolic link was replaced by a regular file holding the referent's bytes, which MUST NOT reproduce the replaced tree's digest"),
		// review-cycle-4 finding R4-1.
		completeness("host-build-reported-as-null", "host", "omission", "schema",
			"a trusted computing base that claims completeness while reporting no kernel build identity at all"),
		completeness("host-build-reported-as-a-bare-string", "host", "uncryptographic-component", "schema",
			"a kernel build identity named by a descriptive string instead of a closed record carrying a digest"),
		completeness("host-build-without-digest", "host", "uncryptographic-component", "schema",
			"a kernel build identity that publishes an identifier and no content digest"),
		completeness("mismatch-host-build-identifier-and-platform", "host", "relation-mismatch", "schema",
			"a kernel build identifier in a grammar the record's own platform cannot report"),
		completeness("host-version-outside-the-release-grammar", "host", "relation-mismatch", "schema",
			"an observed kernel release outside the bounded grammar, which would give one kernel many spellings"),
		completeness("host-build-digest-not-reproducible-from-sources", "host", "digest-mismatch", "conformance-validator",
			"a kernel build digest that the published fixture bytes and the section 2.3.3 construction do not reproduce"),
		completeness("two-kernels-sharing-one-host-build-digest", "host", "digest-mismatch", "implementation",
			"two materially different kernels reporting the same platform, release, and build identifier, which MUST NOT produce one trusted-computing-base record"),
		completeness("host-build-identifier-not-the-declared-source", "host", "relation-mismatch", "conformance-validator",
			"a kernel build identity whose identifier is not the exact value of its platform's declared identifier source"),
		completeness("host-build-digest-carried-from-another-host", "host", "digest-mismatch", "conformance-validator",
			"a kernel build digest published beside a kernel identity, release, or identifier other than the ones it was computed over"),
	)
	return out
}

func evidenceCases() []any {
	cases := []struct {
		name, expected string
		recordValid    bool
	}{
		{"available-capability-reported-not-applied", "hardened_evidence_invalid", false},
		{"unavailable-capability-reported-applied", "hardened_evidence_invalid", false},
		{"unprobed-capability-reported-applied", "hardened_evidence_invalid", false},
		{"missing-capability-entry", "hardened_evidence_invalid", false},
		{"duplicated-capability-entry", "hardened_evidence_invalid", false},
		{"extra-capability-entry-outside-inventory", "hardened_evidence_invalid", false},
		{"missing-guarantee-entry", "hardened_evidence_invalid", false},
		{"guarantee-established-with-unapplied-class", "hardened_evidence_invalid", false},
		{"established-outcome-with-unavailable-capability", "hardened_evidence_invalid", false},
		{"rejected-outcome-without-diagnostic", "hardened_evidence_invalid", false},
		{"unknown-record-version", "hardened_evidence_invalid", false},
		{"unprobed-availability-asserted-without-probe", "hardened_evidence_invalid", false},
		{"portable-record-version-for-hardened-operation", "hardened_profile_claim_forbidden", false},
		{"portable-execution-policy-in-hardened-record", "hardened_profile_claim_forbidden", false},
		{"hardened-record-for-portable-operation", "hardened_profile_claim_forbidden", false},
		{"hardened-profile-identity-without-hardened-policy", "hardened_profile_claim_forbidden", false},
	}
	out := make([]any, 0, len(cases))
	for _, item := range cases {
		out = append(out, map[string]any{
			"name":              item.name,
			"record_valid":      item.recordValid,
			"expected_error":    item.expected,
			"build_permitted":   false,
			"changes_cache_key": false,
			"in_cache_key":      false,
			"in_receipt":        false,
			"in_marker":         false,
			"in_claim":          false,
		})
	}
	return out
}

func noFallbackCases() []any {
	return []any{
		map[string]any{
			"name":                       "unqualified-platform-does-not-fall-back",
			"selected_profile":           hardenedProfileIdentity,
			"resulting_execution_policy": nil,
			"expected_error":             "hardened_profile_unsupported",
			"portable_build_performed":   false,
			"portable_entry_consulted":   false,
			"published":                  false,
		},
		map[string]any{
			"name":                       "unavailable-capability-does-not-fall-back",
			"selected_profile":           hardenedProfileIdentity,
			"resulting_execution_policy": nil,
			"expected_error":             "hardened_capability_unavailable",
			"portable_build_performed":   false,
			"portable_entry_consulted":   false,
			"published":                  false,
		},
		map[string]any{
			"name":                       "hardened-operation-does-not-adopt-portable-entry",
			"selected_profile":           hardenedProfileIdentity,
			"resulting_execution_policy": hardenedExecutionPolicy,
			"expected_error":             nil,
			"portable_build_performed":   false,
			"portable_entry_consulted":   false,
			"published":                  true,
		},
		map[string]any{
			"name":                       "portable-operation-does-not-adopt-hardened-entry",
			"selected_profile":           nil,
			"resulting_execution_policy": portableExecutionPolicy,
			"expected_error":             nil,
			"portable_build_performed":   true,
			"portable_entry_consulted":   true,
			"published":                  true,
		},
	}
}

// -----------------------------------------------------------------------
// vectors/hardened-identity-separation.json
// -----------------------------------------------------------------------

// tcbDigest is curator-hardened-tcb-v1: SHA-256 initialized with the exact
// ASCII algorithm name followed by 0x00, then the length-framed canonical
// bytes of the closed hardened-tcb-v1 record. It is domain-separated so it can
// never be confused with a cache key over the same canonical encoding.
func tcbDigest(record map[string]any) string {
	payload := canonicalValue(record)
	digest := sha256.New()
	digest.Write([]byte(tcbDigestAlgorithm))
	digest.Write([]byte{0})
	var framing [8]byte
	binary.BigEndian.PutUint64(framing[:], uint64(len(payload)))
	digest.Write(framing[:])
	digest.Write(payload)
	return "sha256:" + hex.EncodeToString(digest.Sum(nil))
}

// hardenedIdentity is the closed member a hardened build input adds to the
// portable input. It carries the profile identity and the digest of the
// concrete trusted computing base, so both are inside the hashed identity and
// therefore inside the cache key, the receipt bytes, and receipt_sha256.
func hardenedIdentity(tcb map[string]any) map[string]any {
	return map[string]any{
		"profile": hardenedProfileIdentity,
		"tcb": map[string]any{
			"algorithm":      tcbDigestAlgorithm,
			"content_sha256": tcbDigest(tcb),
		},
	}
}

// hardenedBuildInput is the portable build input with the hardened execution
// policy in the policy slot plus exactly one additional closed member. The
// native target and the toolchain follow the trusted computing base, because a
// hardened receipt whose target contradicts its TCB platform, or whose
// toolchain contradicts its TCB toolchain, is rejected.
func hardenedBuildInput(tcb map[string]any) map[string]any {
	input := buildInputForPlatform(hardenedExecutionPolicy, tcb["platform"].(string))
	input["toolchain"] = deepClone(tcb["toolchain"].(map[string]any))
	input["hardened"] = hardenedIdentity(tcb)
	return input
}

// buildInput returns the exact reserved example input with one execution
// policy substituted. On its own it is the rc.5 policy-slot demonstration, not
// a hardened build input.
func buildInput(policy any) map[string]any {
	return buildInputForPlatform(policy, "macos")
}

// buildInputForPlatform is the same example input targeted at one hardened
// platform. The macos case reproduces the exact bytes rc.5 recorded, so the
// three reserved comparison keys keep their pinned values.
func buildInputForPlatform(policy any, platform string) map[string]any {
	binding := bindingFor(platform)
	buildPolicy := map[string]any{
		"module_mode":         "vendor",
		"network":             "none",
		"workspace":           false,
		"cgo":                 false,
		"compiler_directives": "reject-nonstandard-cgo-import-dynamic-v1",
		"target_mode":         "native",
		"link_mode":           "internal",
		"libgcc":              "none",
		"package_assembly":    false,
		"host_objects":        false,
		"telemetry":           "off-private",
	}
	if policy != nil {
		buildPolicy["execution_policy"] = policy
	}
	return map[string]any{
		"schema_version": 1,
		"driver":         "go-v1",
		"build_source":   map[string]any{"algorithm": "curator-build-source-v1", "content_sha256": buildSourceSHA},
		"build_root":     "build",
		"command":        "golden-tool",
		"source_dir":     "build/cmd/golden-tool",
		"target": map[string]any{
			"goos": binding.goos, "goarch": binding.goarch,
			"tuning": map[string]any{binding.tuningKey: binding.tuningValue},
		},
		"toolchain": toolchainIdentity(binding.goVersion, toolchainSHA),
		"policy":    buildPolicy,
	}
}

// tcbRotation isolates exactly one bound identity. Rotating it must move the
// cache key; a rotation the key does not notice is an unbound identity.
type tcbRotation struct {
	name   string
	fields []string
	// aspects names the trusted-component facets this rotation proves, so
	// coverage is tracked per mutable subfield rather than per array.
	// review-cycle-3 finding R3-1: rotating the array is not rotating the kind.
	aspects []string
	// hostAspects names the kernel-build-identity facets this rotation proves.
	// review-cycle-4 finding R4-1: rotating the host record is not rotating the
	// declared build-identity sources two different kernels differ in.
	hostAspects    []string
	mutate         func(map[string]any)
	packageVisible bool
	reason         string
}

// hostBuildAspects are the mutable facets of the observed kernel build identity.
// Each one is a distinct way two materially different kernels could otherwise
// share a digest, so each needs its own rotation.
var hostBuildAspects = []struct{ aspect, statement string }{
	{"identifier", "the next build of the same kernel release, which moves the declared identifier source"},
	{"source-value", "a rebuild of the same release under the same build identifier, which moves only a declared build-identity source"},
	{"release-binding", "the same declared sources observed under another kernel release, which the digest also covers"},
}

// componentAspects are the mutable facets of a trusted component. Every one of
// them must have at least one rotation, because each is a distinct way two
// materially different trusted bases could otherwise share a digest.
var componentAspects = []struct{ aspect, statement string }{
	{"kind", "the same file reclassified as another kind of trusted component"},
	{"name", "the same component under another name"},
	{"algorithm", "the same kind digested as a single file instead of a tree"},
	{"content", "one byte of a file component"},
	{"tree-membership", "one more entry in a tree component"},
	{"entry-type", "a tree entry that was a regular file becoming a directory"},
	{"link-substitution", "a symbolic link replaced by a regular file holding the referent's bytes"},
	{"component-set", "one additional trusted component the base did not name"},
}

// tcbRotations covers every mutable member of hardened-tcb-v1. The
// package-invisible rotations are the strong ones: nothing a package can see
// changes, so a key that still moves proves the trusted computing base itself
// is what bound it.
func tcbRotations() []tcbRotation {
	return []tcbRotation{
		{
			name: "rotate-parent-identity", fields: []string{"parent_sha256"},
			mutate: func(record map[string]any) { record["parent_sha256"] = updatedParentSHA },
		},
		{
			name: "rotate-supervisor-identity", fields: []string{"supervisor_sha256"},
			mutate: func(record map[string]any) { record["supervisor_sha256"] = updatedSupervisorSHA },
		},
		{
			name: "rotate-worker-identity", fields: []string{"worker_sha256"},
			mutate: func(record map[string]any) { record["worker_sha256"] = updatedWorkerSHA },
		},
		{
			// host.kind is constant and host.identity follows the platform in
			// this revision, so the observed host rotates through the release and
			// the kernel build identity that release was built into.
			name:   "rotate-host-version",
			fields: []string{"host"}, hostAspects: []string{"release-binding"},
			mutate: func(record map[string]any) {
				record["host"] = hostFromBuildFixture("macos-host-build-rotated-release")
			},
		},
		{
			name:   "rotate-host-build-identifier",
			fields: []string{"host"}, hostAspects: []string{"identifier"},
			mutate: func(record map[string]any) {
				record["host"] = hostFromBuildFixture("macos-host-build-rotated-identifier")
			},
		},
		{
			// review-cycle-4 finding R4-1: two materially different kernels that
			// report the same platform, the same release, and the same build
			// identifier. Nothing outside the declared build-identity sources
			// separates them, so if the digest did not cover those sources this
			// rotation would not move the cache key at all.
			name:   "rotate-host-build-source",
			fields: []string{"host"}, hostAspects: []string{"source-value"},
			mutate: func(record map[string]any) {
				record["host"] = hostFromBuildFixture("macos-host-build-recompiled-kernel")
			},
		},
		{
			name: "rotate-backend-version", fields: []string{"backend"},
			mutate: func(record map[string]any) {
				record["backend"].(map[string]any)["version"] = "sandbox-2.1"
			},
		},
		{
			name: "rotate-backend-configuration", fields: []string{"backend"},
			mutate: func(record map[string]any) {
				record["backend"].(map[string]any)["configuration"] = []any{
					configuration("sandbox_profile_dialect", "scheme-v2"),
				}
			},
		},
		{
			name:   "rotate-trusted-component-kind",
			fields: []string{"trusted_components"}, aspects: []string{"kind"},
			mutate: func(record map[string]any) {
				// identity-verifier admits the file algorithm too, so the only
				// thing this rotation changes is the classification itself.
				componentNamed(record, "enforcement-backend-adapter")["kind"] = "identity-verifier"
				record["trusted_components"] = sortComponents(record["trusted_components"].([]any))
			},
		},
		{
			name:   "rotate-trusted-component-name",
			fields: []string{"trusted_components"}, aspects: []string{"name"},
			mutate: func(record map[string]any) {
				componentNamed(record, "enforcement-backend-adapter")["name"] = "enforcement-backend-adapter-v2"
				record["trusted_components"] = sortComponents(record["trusted_components"].([]any))
			},
		},
		{
			name:   "rotate-trusted-component-algorithm",
			fields: []string{"trusted_components"}, aspects: []string{"algorithm"},
			mutate: func(record map[string]any) {
				// The capability-probe kind admits either algorithm, so the same
				// probe shipped as one file instead of a tree is a legal record
				// and still a different trusted computing base.
				probe := componentNamed(record, "capability-probe-suite")
				probe["algorithm"] = componentFileAlgorithm
				probe["content_sha256"] = fixtureDigest("capability-probe-single-file")
			},
		},
		{
			name:   "rotate-trusted-component-content",
			fields: []string{"trusted_components"}, aspects: []string{"content"},
			mutate: func(record map[string]any) {
				componentNamed(record, "enforcement-backend-adapter")["content_sha256"] =
					fixtureDigest("enforcement-backend-adapter-updated")
			},
		},
		{
			name:   "rotate-component-tree-membership",
			fields: []string{"trusted_components"}, aspects: []string{"tree-membership"},
			mutate: func(record map[string]any) {
				componentNamed(record, "capability-probe-suite")["content_sha256"] =
					fixtureDigest("capability-probe-suite-extra-member")
			},
		},
		{
			name:   "rotate-component-entry-type",
			fields: []string{"trusted_components"}, aspects: []string{"entry-type"},
			mutate: func(record map[string]any) {
				componentNamed(record, "capability-probe-suite")["content_sha256"] =
					fixtureDigest("capability-probe-suite-retyped-entry")
			},
		},
		{
			name:   "rotate-component-link-substitution",
			fields: []string{"trusted_components"}, aspects: []string{"link-substitution"},
			mutate: func(record map[string]any) {
				componentNamed(record, "capability-probe-suite")["content_sha256"] =
					fixtureDigest("capability-probe-suite-link-substituted")
			},
		},
		{
			name:   "add-trusted-component",
			fields: []string{"trusted_components"}, aspects: []string{"component-set"},
			mutate: func(record map[string]any) {
				record["trusted_components"] = sortComponents(append(
					record["trusted_components"].([]any),
					component("interpreter", "supervisor-launcher-interpreter", componentFileAlgorithm,
						fixtureDigest("supervisor-launcher-interpreter"))))
			},
		},
		{
			name: "rotate-toolchain-identity", fields: []string{"toolchain"},
			mutate: func(record map[string]any) {
				record["toolchain"].(map[string]any)["content_sha256"] = updatedToolchainSHA
			},
			packageVisible: true,
			reason:         "the fingerprinted toolchain is also a member of the portable build input, so rotating it necessarily moves a value a package can see",
		},
		{
			name:   "rotate-platform-and-backend",
			fields: []string{"platform", "enforcement_backend", "backend", "host", "toolchain"},
			mutate: func(record map[string]any) {
				for key, value := range tcbFor("linux") {
					record[key] = value
				}
			},
			packageVisible: true,
			reason:         "a hardened receipt binds its TCB platform to the native target of its own build input, so another platform is another target",
		},
	}
}

func rotatedRecord(rotation tcbRotation) map[string]any {
	record := hardenedTCB()
	rotation.mutate(record)
	return record
}

func tcbRotationCases() []any {
	base := hardenedBuildInput(hardenedTCB())
	out := make([]any, 0, len(tcbRotations()))
	for _, rotation := range tcbRotations() {
		record := rotatedRecord(rotation)
		input := hardenedBuildInput(record)
		var reason any
		if rotation.reason != "" {
			reason = rotation.reason
		}
		out = append(out, map[string]any{
			"name":                            rotation.name,
			"rotated_fields":                  stringsToAny(rotation.fields),
			"rotated_component_aspects":       stringsToAny(rotation.aspects),
			"rotated_host_build_aspects":      stringsToAny(rotation.hostAspects),
			"tcb":                             record,
			"tcb_digest":                      tcbDigest(record),
			"input":                           input,
			"cache_key":                       canonicalSHA256(input),
			"base_cache_key":                  canonicalSHA256(base),
			"cache_key_differs_from_base":     canonicalSHA256(input) != canonicalSHA256(base),
			"package_visible_input_changed":   rotation.packageVisible,
			"package_visible_change_reason":   reason,
			"receipt_rejected_against_base":   true,
			"marker_rejected_against_base":    true,
			"claim_rejected_against_base":     true,
			"expected_error_if_reused":        "hardened_tcb_identity_invalid",
			"published_from_another_identity": false,
		})
	}
	return out
}

// tcbBoundFields is the completeness statement: every member of the closed
// record, what it identifies, what enforces it, and which rotation proves it
// reaches the cache key. A member with no rotation is one whose value is fixed
// by this profile revision.
func tcbBoundFields() []any {
	rotationsFor := func(field string) []any {
		out := []any{}
		for _, rotation := range tcbRotations() {
			for _, name := range rotation.fields {
				if name == field {
					out = append(out, rotation.name)
					break
				}
			}
		}
		return out
	}
	fields := []struct{ field, identifies, enforcedBy string }{
		{"record_version", "the closed record shape of this profile revision", "schema-constant"},
		{"hardened_profile", "the complete guarantee, capability, ordering, and diagnostic contract", "schema-constant"},
		{"execution_policy", "the execution-policy identity rc.5 reserved", "schema-constant"},
		{"platform", "the hardened platform the operation ran on", "schema-relation"},
		{"enforcement_backend", "the concrete per-platform mechanism that supplied the capability classes", "schema-relation"},
		{"backend", "the observed enforcement-backend version and the configuration the qualification depends on", "schema-closed-record"},
		{"host", "the observed operating-system kernel, its release, and its curator-hardened-host-build-v1 kernel build identity", "schema-closed-record"},
		{"parent_sha256", "the installed manager parent bytes", "schema-digest"},
		{"supervisor_sha256", "the hardened supervisor bytes", "schema-digest"},
		{"worker_sha256", "the domain-root worker bytes", "schema-digest"},
		{"toolchain", "the fingerprinted go launcher and GOROOT tool executables", "schema-closed-record"},
		{"trusted_components", "every additional mutable trusted component, each as a closed cryptographic record", "schema-closed-record"},
	}
	out := make([]any, 0, len(fields))
	for _, item := range fields {
		out = append(out, map[string]any{
			"field":       item.field,
			"identifies":  item.identifies,
			"enforced_by": item.enforcedBy,
			"rotated_by":  rotationsFor(item.field),
		})
	}
	return out
}

// tcbCompleteness names the relations that keep two materially different
// trusted bases from sharing one digest, and says exactly which of them a
// schema can enforce and which the conformance validator enforces.
func tcbCompleteness() map[string]any {
	relation := func(name, statement, enforcedBy, diagnostic string) map[string]any {
		return map[string]any{
			"name": name, "statement": statement,
			"enforced_by": enforcedBy, "expected_error": diagnostic,
		}
	}
	rotationsForAspect := func(aspect string) []any {
		out := []any{}
		for _, rotation := range tcbRotations() {
			for _, name := range rotation.aspects {
				if name == aspect {
					out = append(out, rotation.name)
					break
				}
			}
		}
		return out
	}
	coverage := make([]any, 0, len(componentAspects))
	for _, item := range componentAspects {
		coverage = append(coverage, map[string]any{
			"aspect":     item.aspect,
			"statement":  item.statement,
			"rotated_by": rotationsForAspect(item.aspect),
		})
	}
	rotationsForHostAspect := func(aspect string) []any {
		out := []any{}
		for _, rotation := range tcbRotations() {
			for _, name := range rotation.hostAspects {
				if name == aspect {
					out = append(out, rotation.name)
					break
				}
			}
		}
		return out
	}
	hostCoverage := make([]any, 0, len(hostBuildAspects))
	for _, item := range hostBuildAspects {
		hostCoverage = append(hostCoverage, map[string]any{
			"aspect":     item.aspect,
			"statement":  item.statement,
			"rotated_by": rotationsForHostAspect(item.aspect),
		})
	}
	hostBuildDeclared := map[string]any{}
	for platform, declaration := range hostBuildDeclarations() {
		hostBuildDeclared[platform] = map[string]any{
			"identifier_pattern": declaration.identifierPattern,
			"identifier_source":  declaration.identifierSource,
			"sources":            stringsToAny(declaration.sources),
		}
	}
	return map[string]any{
		"record_version": tcbRecordVersion,
		"closed":         true,
		"unconstrained_string_components_permitted": false,
		"component_digest_algorithms": []any{
			componentFileAlgorithm,
			componentTreeAlgorithm,
		},
		// Which kinds admit which algorithm, so a tree cannot be smuggled in as
		// a file digest under a kind that can only ever name one file.
		"component_algorithm_by_kind": map[string]any{
			"capability-probe":       []any{componentFileAlgorithm, componentTreeAlgorithm},
			"enforcement-adapter":    []any{componentFileAlgorithm, componentTreeAlgorithm},
			"helper-executable":      []any{componentFileAlgorithm},
			"identity-verifier":      []any{componentFileAlgorithm, componentTreeAlgorithm},
			"installed-package-tree": []any{componentTreeAlgorithm},
			"interpreter":            []any{componentFileAlgorithm},
			"sandbox-policy-file":    []any{componentFileAlgorithm},
			"script":                 []any{componentFileAlgorithm},
			"shared-library":         []any{componentFileAlgorithm},
		},
		"component_rotation_coverage": coverage,
		"backend_version_grammar":     backendVersionGrammar,
		// The series token each backend's versions carry. Two series are not
		// comparable, so a claim cannot qualify one backend with another's
		// version line.
		"backend_version_series": map[string]any{
			"linux-namespace-seccomp-v1":  "cgroup2",
			"macos-sandbox-v1":            "sandbox",
			"windows-appcontainer-job-v1": "appcontainer",
		},
		// The canonical kernel identity each platform's TCB must report.
		"canonical_host_identity": map[string]any{
			"linux": "linux", "macos": "darwin", "windows": "windows-nt",
		},
		"host_kind": "operating-system",
		// review-cycle-4 finding R4-1: the observed host is complete only if the
		// kernel build identity is a required closed record over declared
		// sources, so the completeness statement carries the declaration itself.
		"host_build_identity": map[string]any{
			"algorithm":                    hostBuildAlgorithm,
			"required":                     true,
			"nullable":                     false,
			"fixture_version":              hostBuildFixtureVersion,
			"declarations":                 hostBuildDeclared,
			"identifier_equals_source":     true,
			"absent_source_fails_closed":   true,
			"expected_error":               "hardened_tcb_identity_invalid",
			"rejected_before_phase":        "domain-establishment",
			"host_build_rotation_coverage": hostCoverage,
		},
		"bound_fields": tcbBoundFields(),
		"relations": []any{
			relation("platform-to-backend",
				"a platform admits exactly the one enforcement backend its declaration names",
				"schema", "hardened_tcb_identity_invalid"),
			relation("target-to-platform",
				"a hardened receipt's native target goos admits exactly the one TCB platform it maps to",
				"schema", "hardened_tcb_identity_invalid"),
			relation("operating-system-to-backend",
				"a claim's enforcement-backend entry admits exactly the one backend its operating system declares",
				"schema", "hardened_tcb_identity_invalid"),
			relation("claim-operating-system-covers-tcb-platform",
				"a claim's trusted computing base names an operating system the claim itself declares, with the backend that claim declares for it",
				"conformance-validator", "hardened_profile_claim_forbidden"),
			relation("claim-required-configuration-observed-in-tcb",
				"every configuration setting a claim requires is observed with that exact value in the claim's own trusted computing base",
				"conformance-validator", "hardened_tcb_identity_invalid"),
			relation("host-identity-to-platform",
				"a platform admits exactly the one canonical kernel identity its declaration names, and host.kind is operating-system in this revision",
				"schema", "hardened_tcb_identity_invalid"),
			relation("host-build-identifier-to-platform",
				"a platform admits exactly the immutable kernel build identifier grammar its declaration names, and the identifier is the exact value of that platform's declared identifier source",
				"schema", "hardened_tcb_identity_invalid"),
			relation("host-build-digest-reproduces-observed-host",
				"host.build.content_sha256 is the curator-hardened-host-build-v1 digest of the very kernel identity, release, identifier, and declared build-identity sources the same record reports",
				"conformance-validator", "hardened_tcb_identity_invalid"),
			relation("backend-version-series-to-backend",
				"an enforcement backend admits exactly the one hardened-backend-version-v1 series token its declaration names, in the TCB and in a claim minimum_version alike",
				"schema", "hardened_tcb_identity_invalid"),
			relation("component-algorithm-to-kind",
				"a trusted component's digest algorithm is one its kind admits, so a kind that can only name one file cannot carry a tree digest",
				"schema", "hardened_tcb_identity_invalid"),
			relation("claim-backend-version-at-least-minimum",
				"the observed tcb.backend.version is at or above the claim entry's minimum_version under the hardened-backend-version-v1 comparison",
				"conformance-validator", "hardened_tcb_identity_invalid"),
			relation("tcb-toolchain-equals-build-input-toolchain",
				"the TCB toolchain identity is the one the hashed build input carries",
				"conformance-validator", "hardened_tcb_identity_invalid"),
			relation("input-digest-reproduces-tcb-record",
				"input.hardened.tcb.content_sha256 is the curator-hardened-tcb-v1 digest of the receipt's own complete record",
				"conformance-validator", "hardened_tcb_identity_invalid"),
			relation("marker-key-reproducible-from-published-identities",
				"a marker's cache_key follows from the execution policy, profile identity, and TCB record the marker itself publishes",
				"conformance-validator", "hardened_tcb_identity_invalid"),
		},
		"narrower_record_than_actually_trusted": map[string]any{
			"permitted":      false,
			"expected_error": "hardened_tcb_identity_invalid",
			"statement":      "an implementation that starts, loads, or consults a mutable component it does not name in trusted_components reports a trusted computing base narrower than the one it runs on",
		},
	}
}

func writeIdentitySeparationVector(dir string) {
	hardenedInput := hardenedBuildInput(hardenedTCB())
	rotatedInput := hardenedBuildInput(rotatedTCB())
	policySlotInput := buildInput(hardenedExecutionPolicy)
	portableInput := buildInput(portableExecutionPolicy)
	legacyInput := buildInput(nil)

	writeJSON(filepath.Join(dir, "hardened-identity-separation.json"), map[string]any{
		"schema_version":             1,
		"profile_version":            hardenedProfileVersion,
		"hardened_profile":           hardenedProfileIdentity,
		"identity_binding_version":   identityBindingVersion,
		"identity_binding":           identityBinding(),
		"tcb_completeness":           tcbCompleteness(),
		"tcb_rotation_cases":         tcbRotationCases(),
		"component_digest_fixtures":  componentDigestFixtures(),
		"host_build_fixtures":        hostBuildFixtureBlock(),
		"backend_version_comparison": backendVersionComparison(),
		"cache_identity": map[string]any{
			"aliases": false,
			"hardened": map[string]any{
				"execution_policy":   hardenedExecutionPolicy,
				"hardened_profile":   hardenedProfileIdentity,
				"tcb":                hardenedTCB(),
				"input":              hardenedInput,
				"cache_key":          canonicalSHA256(hardenedInput),
				"valid_under_schema": "hardened-build-receipt-v3.schema.json",
				"rejected_by_schema": "build-receipt-v1.schema.json",
			},
			"hardened_rotated_tcb": map[string]any{
				"execution_policy":   hardenedExecutionPolicy,
				"hardened_profile":   hardenedProfileIdentity,
				"tcb":                rotatedTCB(),
				"input":              rotatedInput,
				"cache_key":          canonicalSHA256(rotatedInput),
				"valid_under_schema": "hardened-build-receipt-v3.schema.json",
				"rejected_by_schema": "build-receipt-v1.schema.json",
			},
			"rc5_reserved_policy_slot_only": map[string]any{
				"execution_policy":   hardenedExecutionPolicy,
				"hardened_profile":   nil,
				"tcb":                nil,
				"input":              policySlotInput,
				"cache_key":          canonicalSHA256(policySlotInput),
				"reserved_by":        "conformance/v1/vectors/go-host-execution-policy.json#cache_identity.reserved_hardened",
				"reserved_cache_key": reservedPolicySlotCacheKey,
				"is_hardened_input":  false,
				"valid_under_schema": nil,
				"rejected_by_schema": "hardened-build-receipt-v3.schema.json",
			},
			"portable": map[string]any{
				"execution_policy":   portableExecutionPolicy,
				"hardened_profile":   nil,
				"tcb":                nil,
				"input":              portableInput,
				"cache_key":          canonicalSHA256(portableInput),
				"reserved_cache_key": portableCacheKey,
				"valid_under_schema": "build-receipt-v1.schema.json",
				"rejected_by_schema": "hardened-build-receipt-v3.schema.json",
			},
			"legacy_rc4_without_execution_policy": map[string]any{
				"execution_policy":   nil,
				"hardened_profile":   nil,
				"tcb":                nil,
				"input":              legacyInput,
				"cache_key":          canonicalSHA256(legacyInput),
				"reserved_cache_key": legacyRC4CacheKey,
				"valid_under_schema": nil,
				"rejected_by_schema": "hardened-build-receipt-v3.schema.json",
			},
			"hashed_identity_inputs": []any{
				"the curator-hardened-tcb-v1 digest of the concrete trusted computing base",
				"the execution-policy identity inside the canonical build policy object",
				"the hardened profile identity inside the closed hardened input member",
			},
			"excluded_from_hashed_identity": []any{
				"the per-operation hardened capability-evidence record",
			},
		},
		"receipt_separation": []any{
			map[string]any{"driver": "go-v1", "portable_schema_version": 1, "hardened_schema_version": 3, "portable_schema_widened": false, "hardened_receipt_binds": []any{"execution_policy", "hardened_profile", "tcb"}},
			map[string]any{"driver": "go-repository-v1", "portable_schema_version": 2, "hardened_schema_version": 4, "portable_schema_widened": false, "hardened_receipt_binds": []any{"execution_policy", "hardened_profile", "tcb"}},
		},
		"marker_separation": map[string]any{
			"portable_schema_versions":           []any{1, 2, 3},
			"hardened_schema_version":            4,
			"portable_schema_widened":            false,
			"hardened_record_in_portable_marker": false,
			"portable_record_in_hardened_marker": false,
			"hardened_record_requires":           []any{"execution_policy", "hardened_profile", "tcb"},
		},
		"claim_separation": map[string]any{
			"portable_schema_version":              3,
			"hardened_schema_version":              4,
			"portable_admits":                      []any{portableExecutionPolicy},
			"hardened_admits":                      []any{hardenedExecutionPolicy},
			"portable_schema_widened":              false,
			"hardened_claim_requires":              []any{"execution_policy", "hardened_profile", "tcb"},
			"hardened_claims_emitted":              []any{},
			"hardened_qualified_operating_systems": []any{},
		},
		"cross_profile_reuse_cases": crossProfileReuseCases(),
	})
}

// identityBinding is the single mechanically enforced model that answers where
// each identity lives. Every "yes" below is checked by tools/validate_hardened.py
// against real artifacts, not asserted in prose.
func identityBinding() map[string]any {
	binding := func(identity, value string, hashed, receipt, marker, claim, reuse bool) map[string]any {
		return map[string]any{
			"identity":              identity,
			"value":                 value,
			"in_hashed_build_input": hashed,
			"in_receipt_bytes":      receipt,
			"in_install_marker":     marker,
			"in_conformance_claim":  claim,
			"binds_cache_reuse":     reuse,
		}
	}
	return map[string]any{
		"version":              identityBindingVersion,
		"tcb_digest_algorithm": tcbDigestAlgorithm,
		"tcb_digest_framing": "SHA-256 initialized with ASCII " + tcbDigestAlgorithm +
			" followed by 0x00, then uint64be(length) and the canonical bytes of the closed hardened-tcb-v1 record",
		"identities": []any{
			binding("execution-policy", hardenedExecutionPolicy, true, true, true, true, true),
			binding("hardened-profile", hardenedProfileIdentity, true, true, true, true, true),
			binding("trusted-computing-base", tcbRecordVersion, true, true, true, true, true),
			binding("capability-evidence", evidenceRecordVersion, false, false, false, false, false),
		},
		"result_only_records":                 []any{evidenceRecordVersion},
		"reuse_rule":                          "a lookup recomputes the cache key from the profile identity and the current verified trusted-computing-base digest, so an entry produced under another profile revision or another trusted computing base cannot be a hit",
		"cross_tcb_reuse":                     false,
		"cross_profile_reuse":                 false,
		"in_place_upgrade":                    false,
		"per_host_key_divergence_is_intended": true,
	}
}

func crossProfileReuseCases() []any {
	reuse := func(name, reader, entry string, readerTCB, entryTCB any, result string, publishes bool) map[string]any {
		return map[string]any{
			"name":         name,
			"reader":       reader,
			"entry":        entry,
			"reader_tcb":   readerTCB,
			"entry_tcb":    entryTCB,
			"result":       result,
			"upgrades":     false,
			"publishes":    publishes,
			"adopts_bytes": result == "hit",
		}
	}
	current := tcbDigest(hardenedTCB())
	rotated := tcbDigest(rotatedTCB())
	return []any{
		reuse("hardened-reader-sees-portable-entry", hardenedExecutionPolicy, portableExecutionPolicy, current, nil, "miss", false),
		reuse("portable-reader-sees-hardened-entry", portableExecutionPolicy, hardenedExecutionPolicy, nil, current, "miss", false),
		reuse("hardened-reader-sees-pre-revision-entry", hardenedExecutionPolicy, "", current, nil, "miss", false),
		reuse("hardened-reader-sees-policy-slot-only-entry", hardenedExecutionPolicy, hardenedExecutionPolicy, current, nil, "miss", false),
		reuse("hardened-reader-sees-entry-from-another-tcb", hardenedExecutionPolicy, hardenedExecutionPolicy, current, rotated, "miss", false),
		reuse("hardened-reader-sees-its-own-entry", hardenedExecutionPolicy, hardenedExecutionPolicy, current, current, "hit", true),
	}
}

// -----------------------------------------------------------------------
// schema cases
// -----------------------------------------------------------------------

func validHardenedReceiptV3() map[string]any {
	input := hardenedBuildInput(hardenedTCB())
	return map[string]any{
		"schema_version": 3,
		"cache_key":      canonicalSHA256(input),
		"input":          input,
		"tcb":            hardenedTCB(),
		"artifact":       map[string]any{"path": "bin/golden-tool", "sha256": artifactSHA, "size": 1024},
	}
}

func validHardenedReceiptV4() map[string]any {
	macos := bindingFor("macos")
	input := map[string]any{
		"schema_version": 2,
		"driver":         "go-repository-v1",
		"hardened":       hardenedIdentity(hardenedTCB()),
		"source": map[string]any{
			"repository": "golden-tools",
			"declared": map[string]any{
				"identity":      map[string]any{"kind": "network-git", "value": "github.com/example/golden-tools"},
				"transport":     "https",
				"locked_commit": map[string]any{"object_format": "sha1", "hex": fixedCommit},
			},
			"effective": map[string]any{
				"identity":      map[string]any{"kind": "network-git", "value": "github.com/example/golden-tools"},
				"transport":     "https",
				"object_format": "sha1",
				"commit":        fixedCommit,
				"substituted":   false,
				"build_source":  map[string]any{"algorithm": "curator-build-source-v1", "content_sha256": externalSHA},
			},
			"descriptor": map[string]any{"path": "skill-build.json", "target": "golden-tool"},
		},
		"command":    "golden-tool",
		"build_root": ".",
		"source_dir": "cmd/golden-tool",
		"target": map[string]any{
			"goos": macos.goos, "goarch": macos.goarch,
			"tuning": map[string]any{macos.tuningKey: macos.tuningValue},
		},
		"toolchain": toolchainIdentity(macos.goVersion, toolchainSHA),
		"policy": map[string]any{
			"module_mode": "vendor", "network": "none", "workspace": false, "cgo": false,
			"compiler_directives": "reject-nonstandard-cgo-import-dynamic-v1",
			"target_mode":         "native", "link_mode": "internal", "libgcc": "none",
			"package_assembly": false, "host_objects": false, "telemetry": "off-private",
			"execution_policy": hardenedExecutionPolicy, "source_kind": "locked-external-git-v1",
		},
	}
	return map[string]any{
		"schema_version": 4,
		"cache_key":      canonicalSHA256(input),
		"input":          input,
		"tcb":            hardenedTCB(),
		"artifact":       map[string]any{"path": "bin/golden-tool", "sha256": artifactSHA, "size": 2048},
	}
}

// platformBinding is everything the example fixtures need to keep one hardened
// platform internally consistent: the enforcement backend the platform declares,
// the observed host and backend identities the qualification depends on, and the
// native target the build input for that platform carries.
type platformBinding struct {
	backend        string
	backendVersion string
	backendConfig  []any
	host           map[string]any
	goos           string
	goarch         string
	tuningKey      string
	tuningValue    string
	goVersion      string
}

func configuration(setting, observed string) map[string]any {
	return map[string]any{"setting": setting, "observed_value": observed}
}

func requirement(setting, required string) map[string]any {
	return map[string]any{"setting": setting, "required_value": required}
}

// platformBindings is the one place a platform, its declared backend, its
// observed host, and its native target are tied together. Every fixture derives
// from it, so a mismatched pair cannot be written by accident.
func platformBindings() map[string]platformBinding {
	return map[string]platformBinding{
		"macos": {
			backend:        "macos-sandbox-v1",
			backendVersion: "sandbox-2.0",
			backendConfig:  []any{configuration("sandbox_profile_dialect", "scheme-v1")},
			host:           hostFromBuildFixture("macos-host-build"),
			goos:           "darwin", goarch: "arm64",
			tuningKey: "GOARM64", tuningValue: "v8.0",
			goVersion: "go version go1.26.1 darwin/arm64",
		},
		"linux": {
			backend:        "linux-namespace-seccomp-v1",
			backendVersion: "cgroup2-6.12",
			backendConfig: []any{
				configuration("cgroup.version", "2"),
				configuration("user_namespaces.unprivileged", "enabled"),
			},
			host: hostFromBuildFixture("linux-host-build"),
			goos: "linux", goarch: "arm64",
			tuningKey: "GOARM64", tuningValue: "v8.0",
			goVersion: "go version go1.26.1 linux/arm64",
		},
		"windows": {
			backend:        "windows-appcontainer-job-v1",
			backendVersion: "appcontainer-10.0.26100",
			backendConfig:  []any{configuration("job_object.nested", "enabled")},
			host:           hostFromBuildFixture("windows-host-build"),
			goos:           "windows", goarch: "amd64",
			tuningKey: "GOAMD64", tuningValue: "v1",
			goVersion: "go version go1.26.1 windows/amd64",
		},
	}
}

func bindingFor(platform string) platformBinding {
	binding, ok := platformBindings()[platform]
	if !ok {
		panic("unknown hardened platform " + platform)
	}
	return binding
}

func toolchainIdentity(goVersion, contentSHA string) map[string]any {
	return map[string]any{
		"algorithm": "curator-go-toolchain-v1", "go_relpath": "bin/go",
		"go_version": goVersion, "content_sha256": contentSHA,
	}
}

// -----------------------------------------------------------------------
// trusted-component digest algorithms
// -----------------------------------------------------------------------

// componentEntry is one record of a curator-hardened-component-tree-v1 walk.
// kind is ASCII D, F, or L; a directory payload is empty, a file payload is the
// exact bytes, and a link payload is the exact readlink value.
type componentEntry struct {
	kind    string
	path    string
	payload string
}

// componentFixture is an independently recomputable component digest. The
// fixture publishes the exact bytes the algorithm consumes, so a reader that
// implements protocol/hardened-execution.md section 2.3.1 reproduces
// expected_sha256 without running this generator. review-cycle-3 finding R3-1:
// naming an algorithm is not defining one.
type componentFixture struct {
	name      string
	statement string
	algorithm string
	// content is the file bytes for the file algorithm.
	content string
	// entries is the sorted walk for the tree algorithm.
	entries []componentEntry
}

func (fixture componentFixture) digest() string {
	if fixture.algorithm == componentFileAlgorithm {
		return componentFileDigest(fixture.content)
	}
	return componentTreeDigest(fixture.entries)
}

func writeFramed(digest hash.Hash, payload string) {
	var framing [8]byte
	binary.BigEndian.PutUint64(framing[:], uint64(len(payload)))
	digest.Write(framing[:])
	digest.Write([]byte(payload))
}

// componentFileDigest hashes a single regular file. The component's location is
// not an input: the record around it carries kind and name, and the whole
// record is inside curator-hardened-tcb-v1.
func componentFileDigest(content string) string {
	digest := sha256.New()
	digest.Write([]byte(componentFileAlgorithm))
	digest.Write([]byte{0})
	digest.Write([]byte("F"))
	writeFramed(digest, content)
	return "sha256:" + hex.EncodeToString(digest.Sum(nil))
}

// componentTreeDigest hashes a directory tree. Entry paths sort in unsigned
// bytewise order, which is exactly Go's string comparison over UTF-8 bytes, and
// the entry kind is hashed so a link substitution cannot reproduce the digest of
// the tree it replaced.
func componentTreeDigest(entries []componentEntry) string {
	sorted := append([]componentEntry(nil), entries...)
	sort.Slice(sorted, func(left, right int) bool { return sorted[left].path < sorted[right].path })
	for index := 1; index < len(sorted); index++ {
		if sorted[index].path == sorted[index-1].path {
			panic("duplicate component tree path " + sorted[index].path)
		}
	}
	digest := sha256.New()
	digest.Write([]byte(componentTreeAlgorithm))
	digest.Write([]byte{0})
	for _, entry := range sorted {
		if entry.kind != "D" && entry.kind != "F" && entry.kind != "L" {
			panic("unknown component tree entry kind " + entry.kind)
		}
		digest.Write([]byte(entry.kind))
		writeFramed(digest, entry.path)
		writeFramed(digest, entry.payload)
	}
	return "sha256:" + hex.EncodeToString(digest.Sum(nil))
}

const (
	networkProbeBytes = "#!probe network\ndeny-all\n"
	writeProbeBytes   = "#!probe write\nconfine build-root\n"
	execProbeBytes    = "#!probe exec\nallowlist exact\n"
)

// probeSuiteEntries is the base capability-probe tree: two regular probe files,
// their directory, and a relative symbolic link to one of them.
func probeSuiteEntries() []componentEntry {
	return []componentEntry{
		{kind: "D", path: "probes", payload: ""},
		{kind: "F", path: "probes/network.probe", payload: networkProbeBytes},
		{kind: "F", path: "probes/write.probe", payload: writeProbeBytes},
		{kind: "L", path: "probes/current.probe", payload: "network.probe"},
	}
}

// componentFixtures are the fixtures the suite publishes. Every trusted-component
// digest anywhere in the hardened suite comes from one of them, so no component
// carries an invented constant.
func componentFixtures() []componentFixture {
	linkReplaced := probeSuiteEntries()
	for index := range linkReplaced {
		if linkReplaced[index].path == "probes/current.probe" {
			// The exact substitution the tree algorithm must notice: a regular
			// file holding the referent's own bytes, in the link's place.
			linkReplaced[index] = componentEntry{
				kind: "F", path: "probes/current.probe", payload: networkProbeBytes,
			}
		}
	}
	retyped := []componentEntry{
		{kind: "D", path: "probes", payload: ""},
		// probes/network.probe is a directory here, not a regular file.
		{kind: "D", path: "probes/network.probe", payload: ""},
		{kind: "F", path: "probes/network.probe/main", payload: networkProbeBytes},
		{kind: "F", path: "probes/write.probe", payload: writeProbeBytes},
		{kind: "L", path: "probes/current.probe", payload: "network.probe"},
	}
	return []componentFixture{
		{
			name:      "capability-probe-suite",
			statement: "the base capability-probe tree: a directory, two regular probe files, and a relative link to one of them",
			algorithm: componentTreeAlgorithm,
			entries:   probeSuiteEntries(),
		},
		{
			name:      "capability-probe-suite-extra-member",
			statement: "the same tree with one more probe file, so tree membership alone moves the digest",
			algorithm: componentTreeAlgorithm,
			entries:   append(probeSuiteEntries(), componentEntry{kind: "F", path: "probes/exec.probe", payload: execProbeBytes}),
		},
		{
			name:      "capability-probe-suite-retyped-entry",
			statement: "the same tree with a regular file replaced by a directory of the same name, so the entry kind alone moves the digest",
			algorithm: componentTreeAlgorithm,
			entries:   retyped,
		},
		{
			name:      "capability-probe-suite-link-substituted",
			statement: "the same tree with the symbolic link replaced by a regular file holding the referent's exact bytes, which MUST NOT reproduce the base digest",
			algorithm: componentTreeAlgorithm,
			entries:   linkReplaced,
		},
		{
			name:      "capability-probe-single-file",
			statement: "one probe shipped as a single regular file, which the capability-probe kind also admits",
			algorithm: componentFileAlgorithm,
			content:   networkProbeBytes,
		},
		{
			name:      "enforcement-backend-adapter",
			statement: "the enforcement-backend adapter as a single regular file",
			algorithm: componentFileAlgorithm,
			content:   "#!adapter macos-sandbox-v1\ndeny default\n",
		},
		{
			name:      "enforcement-backend-adapter-updated",
			statement: "the same adapter after a byte changed, so component content alone moves the digest",
			algorithm: componentFileAlgorithm,
			content:   "#!adapter macos-sandbox-v1\ndeny default\ndeny network*\n",
		},
		{
			name:      "supervisor-launcher-interpreter",
			statement: "an interpreter an implementation may additionally trust, which the interpreter kind admits only as a file",
			algorithm: componentFileAlgorithm,
			content:   "#!interpreter launcher\n",
		},
		{
			name:      "empty-file-component",
			statement: "an empty regular file, which hashes the domain prefix plus F and uint64be(0)",
			algorithm: componentFileAlgorithm,
			content:   "",
		},
		{
			name:      "empty-tree-component",
			statement: "an empty directory tree, which hashes the domain prefix alone and MUST NOT collide with the empty file",
			algorithm: componentTreeAlgorithm,
			entries:   nil,
		},
	}
}

// -----------------------------------------------------------------------
// curator-hardened-host-build-v1
// -----------------------------------------------------------------------

// hostBuildSource is one declared observation of the running kernel. Its name
// and its exact observed bytes are both hashed, so a value moved across a source
// boundary cannot reproduce another host's build identity.
type hostBuildSource struct {
	name  string
	value string
}

// hostBuildDeclaration is what protocol/hardened-execution.md section 6.3
// declares per platform: the grammar of the immutable build identifier, the
// source that identifier is read from, and the ordered closed list of sources
// the digest covers.
type hostBuildDeclaration struct {
	identifierPattern string
	identifierSource  string
	sources           []string
}

// hostBuildDeclarations mirrors section 6.3. The identifier patterns are the
// exact strings hardened-common.schema.json enforces, so the document, the
// schema, and this generator cannot drift apart.
func hostBuildDeclarations() map[string]hostBuildDeclaration {
	return map[string]hostBuildDeclaration{
		"linux": {
			identifierPattern: `^[0-9a-f]{32,128}(?![\s\S])`,
			identifierSource:  "kernel.build-id",
			sources:           []string{"kernel.build-id", "kernel.osrelease", "kernel.version-string"},
		},
		"macos": {
			identifierPattern: `^[0-9]{1,3}[A-Z][0-9]{1,6}[a-z]?(?![\s\S])`,
			identifierSource:  "kern.osversion",
			sources:           []string{"kern.osversion", "kern.osproductversion", "kern.version"},
		},
		"windows": {
			identifierPattern: `^[0-9]{1,7}\.[0-9]{1,7}(?![\s\S])`,
			identifierSource:  "kernel.current-build-and-ubr",
			sources: []string{
				"kernel.current-build-and-ubr", "kernel.build-lab-ex", "kernel.image-file-version",
			},
		},
	}
}

func hostBuildDeclarationFor(platform string) hostBuildDeclaration {
	declaration, ok := hostBuildDeclarations()[platform]
	if !ok {
		panic("unknown hardened platform " + platform)
	}
	return declaration
}

// hostBuildDigest is the section 2.3.3 construction. The observed kernel
// identity, release, and build identifier are inside the digest, so a build
// identity cannot be carried to a host that reports a different tuple; the
// source count and the per-field framing are inside it so bytes shifted across a
// field boundary produce a different value.
func hostBuildDigest(identity, version, identifier string, sources []hostBuildSource) string {
	digest := sha256.New()
	digest.Write([]byte(hostBuildAlgorithm))
	digest.Write([]byte{0})
	writeFramed(digest, identity)
	writeFramed(digest, version)
	writeFramed(digest, identifier)
	var framing [8]byte
	binary.BigEndian.PutUint64(framing[:], uint64(len(sources)))
	digest.Write(framing[:])
	for _, source := range sources {
		writeFramed(digest, source.name)
		writeFramed(digest, source.value)
	}
	return "sha256:" + hex.EncodeToString(digest.Sum(nil))
}

// hostBuildFixture is an independently recomputable kernel build identity. It
// publishes the exact bytes the construction consumes, so a reader that
// implements section 2.3.3 reproduces expected_sha256 without running this
// generator.
type hostBuildFixture struct {
	name      string
	statement string
	platform  string
	identity  string
	version   string
	sources   []hostBuildSource
}

// identifier is always the value of the platform's declared identifier source:
// section 2.3.3 requires the two to be the same bytes, so the fixture derives
// one from the other rather than restating it.
func (fixture hostBuildFixture) identifier() string {
	declaration := hostBuildDeclarationFor(fixture.platform)
	for _, source := range fixture.sources {
		if source.name == declaration.identifierSource {
			return source.value
		}
	}
	panic("host build fixture " + fixture.name + " has no identifier source")
}

func (fixture hostBuildFixture) digest() string {
	declaration := hostBuildDeclarationFor(fixture.platform)
	if len(fixture.sources) != len(declaration.sources) {
		panic("host build fixture " + fixture.name + " does not observe its platform's sources")
	}
	for index, source := range fixture.sources {
		if source.name != declaration.sources[index] {
			panic("host build fixture " + fixture.name + " observes sources out of declared order")
		}
		if source.value == "" {
			panic("host build fixture " + fixture.name + " observes an empty source")
		}
	}
	if !regexp.MustCompile(strings.TrimSuffix(declaration.identifierPattern, `(?![\s\S])`) + "$").
		MatchString(fixture.identifier()) {
		panic("host build fixture " + fixture.name + " carries an identifier its platform cannot report")
	}
	return hostBuildDigest(fixture.identity, fixture.version, fixture.identifier(), fixture.sources)
}

const (
	darwinKernelVersion = "Darwin Kernel Version 25.0.0: Mon Jan  6 21:00:00 PST 2026; " +
		"root:xnu-12377.1.9~1/RELEASE_ARM64_T6000"
	// The same kernel release and the same build identifier, rebuilt: exactly the
	// pair review cycle 4 showed an optional descriptive build string could not
	// separate.
	darwinRecompiledKernelVersion = "Darwin Kernel Version 25.0.0: Tue Jan  7 09:30:00 PST 2026; " +
		"root:xnu-12377.1.9~1/RELEASE_ARM64_T6000"
	linuxBuildID       = "4f2a1c8e6b90d3574a1e2f8c0b7d69315ae4c2f8"
	linuxKernelVersion = "Linux version 6.12.0 (build@builder) (gcc 14.2.0, GNU ld 2.43) " +
		"#1 SMP PREEMPT_DYNAMIC Mon Jan  6 21:00:00 UTC 2026"
)

func source(name, value string) hostBuildSource {
	return hostBuildSource{name: name, value: value}
}

// macosSources builds the declared macOS observation list in declared order.
func macosSources(osVersion, productVersion, kernelVersion string) []hostBuildSource {
	return []hostBuildSource{
		source("kern.osversion", osVersion),
		source("kern.osproductversion", productVersion),
		source("kern.version", kernelVersion),
	}
}

// hostBuildFixtures are the kernel build identities the suite publishes. Every
// host.build digest anywhere in the hardened suite comes from one of them, so no
// observed host carries an invented identity.
func hostBuildFixtures() []hostBuildFixture {
	return []hostBuildFixture{
		{
			name:      "macos-host-build",
			statement: "the example macOS host: build identifier, product version, and the full kernel version string",
			platform:  "macos", identity: "darwin", version: "25.0.0",
			sources: macosSources("25A123", "26.0", darwinKernelVersion),
		},
		{
			name: "macos-host-build-recompiled-kernel",
			statement: "the same platform, the same release, and the same build identifier, " +
				"rebuilt: only the kernel version string differs, and the digest MUST NOT reproduce the base",
			platform: "macos", identity: "darwin", version: "25.0.0",
			sources: macosSources("25A123", "26.0", darwinRecompiledKernelVersion),
		},
		{
			name:      "macos-host-build-rotated-release",
			statement: "the same declared sources under another observed kernel release, which isolates the release binding inside the digest",
			platform:  "macos", identity: "darwin", version: "25.1.0",
			sources: macosSources("25A123", "26.0", darwinKernelVersion),
		},
		{
			name:      "macos-host-build-rotated-identifier",
			statement: "the next build of the same release: the identifier source moves, so both the identifier and the digest move with it",
			platform:  "macos", identity: "darwin", version: "25.0.0",
			sources: macosSources("25A124", "26.0", darwinKernelVersion),
		},
		{
			name: "macos-host-build-source-boundary-shift",
			statement: "a probe, not a host: one byte moved from the front of kern.version to the end of " +
				"kern.osproductversion, so the declared source values concatenate to exactly the base's bytes. " +
				"An implementation that hashed the observed values as one blob would alias this probe with the base",
			platform: "macos", identity: "darwin", version: "25.0.0",
			sources: macosSources(
				"25A123",
				"26.0"+darwinKernelVersion[:1],
				darwinKernelVersion[1:],
			),
		},
		{
			name:      "linux-host-build",
			statement: "the example Linux host: the running kernel image build id, the release, and the full version string",
			platform:  "linux", identity: "linux", version: "6.12.0",
			sources: []hostBuildSource{
				source("kernel.build-id", linuxBuildID),
				source("kernel.osrelease", "6.12.0"),
				source("kernel.version-string", linuxKernelVersion),
			},
		},
		{
			name:      "windows-host-build",
			statement: "the example Windows host: the build and update revision, the build lab string, and the kernel image file version",
			platform:  "windows", identity: "windows-nt", version: "10.0.26100",
			sources: []hostBuildSource{
				source("kernel.current-build-and-ubr", "26100.1"),
				source("kernel.build-lab-ex", "26100.1.amd64fre.ge_release.260106-2100"),
				source("kernel.image-file-version", "10.0.26100.1"),
			},
		},
	}
}

func hostBuildFixtureFor(name string) hostBuildFixture {
	for _, fixture := range hostBuildFixtures() {
		if fixture.name == name {
			return fixture
		}
	}
	panic("unknown host build fixture " + name)
}

// hostFromBuildFixture is the only way an observed host enters the suite: the
// kernel identity, the release, and the build identity all come from one
// fixture, so a record cannot pair one host's tuple with another host's digest.
func hostFromBuildFixture(name string) map[string]any {
	fixture := hostBuildFixtureFor(name)
	return map[string]any{
		"kind":     "operating-system",
		"identity": fixture.identity,
		"version":  fixture.version,
		"build": map[string]any{
			"algorithm":      hostBuildAlgorithm,
			"identifier":     fixture.identifier(),
			"content_sha256": fixture.digest(),
		},
	}
}

// hostBuildFixtureBlock publishes the fixtures with the exact bytes and lengths
// a reader needs to recompute every expected digest independently.
func hostBuildFixtureBlock() map[string]any {
	declarations := map[string]any{}
	for platform, declaration := range hostBuildDeclarations() {
		declarations[platform] = map[string]any{
			"identifier_pattern": declaration.identifierPattern,
			"identifier_source":  declaration.identifierSource,
			"sources":            stringsToAny(declaration.sources),
		}
	}
	published := make([]any, 0, len(hostBuildFixtures()))
	for _, fixture := range hostBuildFixtures() {
		sources := make([]any, 0, len(fixture.sources))
		for _, item := range fixture.sources {
			sources = append(sources, map[string]any{
				"name":              item.name,
				"name_byte_length":  len(item.name),
				"value":             item.value,
				"value_byte_length": len(item.value),
			})
		}
		published = append(published, map[string]any{
			"name":                     fixture.name,
			"statement":                fixture.statement,
			"platform":                 fixture.platform,
			"host_identity":            fixture.identity,
			"host_version":             fixture.version,
			"identifier":               fixture.identifier(),
			"identifier_byte_length":   len(fixture.identifier()),
			"sources":                  sources,
			"source_count":             len(fixture.sources),
			"expected_sha256":          fixture.digest(),
			"conforming_observed_host": fixture.name != "macos-host-build-source-boundary-shift",
		})
	}
	return map[string]any{
		"version":                     hostBuildFixtureVersion,
		"algorithm":                   hostBuildAlgorithm,
		"domain_separation":           "the exact ASCII algorithm identifier followed by 0x00",
		"framing":                     "uint64be byte length before every variable-length field, and uint64be over the declared source count",
		"hashed_order":                []any{"identity", "version", "identifier", "source_count", "source name and value pairs in declared order"},
		"declarations":                declarations,
		"nullable_build_permitted":    false,
		"unreadable_source_permitted": false,
		"fixtures":                    published,
		"all_digests_distinct":        true,
	}
}

// -----------------------------------------------------------------------
// hardened-backend-version-v1
// -----------------------------------------------------------------------

var backendVersionPattern = regexp.MustCompile(`^([a-z][a-z0-9]*)-((?:0|[1-9][0-9]{0,8})(?:\.(?:0|[1-9][0-9]{0,8})){0,3})$`)

// parseBackendVersion returns the series token and the numeric components
// right-padded to four, or ok=false when the value is outside the grammar of
// protocol/hardened-execution.md section 2.3.4.
func parseBackendVersion(value string) (string, [4]int, bool) {
	var components [4]int
	match := backendVersionPattern.FindStringSubmatch(value)
	if match == nil {
		return "", components, false
	}
	for index, part := range strings.Split(match[2], ".") {
		number, err := strconv.Atoi(part)
		if err != nil {
			return "", components, false
		}
		components[index] = number
	}
	return match[1], components, true
}

// backendVersionAtLeast reports whether observed is at or above minimum.
// comparable is false when either value is malformed or the two series differ,
// which is not a lower or higher result but an invalid comparison.
func backendVersionAtLeast(observed, minimum string) (satisfied bool, comparable bool) {
	observedSeries, observedParts, observedOK := parseBackendVersion(observed)
	minimumSeries, minimumParts, minimumOK := parseBackendVersion(minimum)
	if !observedOK || !minimumOK || observedSeries != minimumSeries {
		return false, false
	}
	for index := range observedParts {
		if observedParts[index] != minimumParts[index] {
			return observedParts[index] > minimumParts[index], true
		}
	}
	return true, true
}

// backendVersionComparison publishes the comparison cases a reader re-evaluates.
// review-cycle-3 finding R3-2: the normative "at or above" was never compared,
// so a backend version of 0 satisfied a minimum of 999999.
func backendVersionComparison() map[string]any {
	cases := []struct{ name, observed, minimum, statement string }{
		{"above-minimum", "cgroup2-6.12", "cgroup2-6.1",
			"an observed version above the declared minimum qualifies"},
		{"equal-to-minimum", "cgroup2-6.1", "cgroup2-6.1",
			"an observed version exactly at the declared minimum qualifies"},
		{"equal-after-padding", "sandbox-2", "sandbox-2.0.0",
			"a missing numeric component is zero, so these two values are equal"},
		{"below-minimum", "cgroup2-6.1", "cgroup2-6.12",
			"an observed version below the declared minimum does not qualify"},
		{"below-minimum-major", "sandbox-1.99", "sandbox-2.0",
			"a lower leading component loses regardless of the components after it"},
		{"below-minimum-not-lexical", "cgroup2-6.9", "cgroup2-6.10",
			"components compare as integers, so 9 is below 10 even though it sorts after it as a string"},
		{"reviewer-probe-zero-against-huge", "cgroup2-0", "cgroup2-999999",
			"the exact review-cycle-3 probe: a backend version of zero does not satisfy a minimum of 999999"},
		{"incomparable-series", "cgroup2-6.12", "sandbox-2.0",
			"two backends' version lines have no ordering, so this is invalid rather than higher or lower"},
		{"malformed-observed-leading-zero", "cgroup2-06.1", "cgroup2-6.1",
			"a component with a leading zero is outside the grammar"},
		{"malformed-observed-no-series", "6.1", "cgroup2-6.1",
			"a bare number carries no series, so it identifies no backend"},
		{"malformed-observed-empty-number", "cgroup2-", "cgroup2-6.1",
			"a series with no number is outside the grammar"},
		{"malformed-minimum-too-many-components", "cgroup2-6.1", "cgroup2-1.2.3.4.5",
			"at most four numeric components are admitted"},
		{"malformed-minimum-not-a-version", "cgroup2-6.1", "latest",
			"a minimum that is prose cannot be compared with anything"},
	}
	out := make([]any, 0, len(cases))
	for _, item := range cases {
		satisfied, comparable := backendVersionAtLeast(item.observed, item.minimum)
		_, _, observedOK := parseBackendVersion(item.observed)
		_, _, minimumOK := parseBackendVersion(item.minimum)
		out = append(out, map[string]any{
			"name":            item.name,
			"statement":       item.statement,
			"observed":        item.observed,
			"minimum":         item.minimum,
			"observed_valid":  observedOK,
			"minimum_valid":   minimumOK,
			"comparable":      comparable,
			"satisfied":       satisfied,
			"expected_error":  "hardened_tcb_identity_invalid",
			"claim_qualifies": satisfied,
			"published":       false,
		})
	}
	return map[string]any{
		"grammar":                 backendVersionGrammar,
		"shape":                   "series \"-\" number ( \".\" number ){0,3}",
		"number":                  "0 or a nonzero digit followed by at most eight more digits",
		"missing_component_value": 0,
		"cross_series_comparison": "invalid",
		"cases":                   out,
	}
}

func fixtureFor(name string) componentFixture {
	for _, fixture := range componentFixtures() {
		if fixture.name == name {
			return fixture
		}
	}
	panic("unknown component fixture " + name)
}

// fixtureDigest is the only way a trusted-component digest enters the suite.
func fixtureDigest(name string) string {
	return fixtureFor(name).digest()
}

// componentDigestFixtures publishes the fixtures with the exact bytes and
// lengths a reader needs to recompute every expected digest independently.
func componentDigestFixtures() map[string]any {
	published := make([]any, 0, len(componentFixtures()))
	for _, fixture := range componentFixtures() {
		record := map[string]any{
			"name":            fixture.name,
			"statement":       fixture.statement,
			"algorithm":       fixture.algorithm,
			"expected_sha256": fixture.digest(),
			"file":            nil,
			"entries":         nil,
		}
		if fixture.algorithm == componentFileAlgorithm {
			record["file"] = map[string]any{
				"content":             fixture.content,
				"content_byte_length": len(fixture.content),
			}
		} else {
			entries := make([]any, 0, len(fixture.entries))
			sorted := append([]componentEntry(nil), fixture.entries...)
			sort.Slice(sorted, func(left, right int) bool { return sorted[left].path < sorted[right].path })
			for _, entry := range sorted {
				entries = append(entries, map[string]any{
					"kind":                entry.kind,
					"path":                entry.path,
					"path_byte_length":    len(entry.path),
					"payload":             entry.payload,
					"payload_byte_length": len(entry.payload),
				})
			}
			record["entries"] = entries
		}
		published = append(published, record)
	}
	return map[string]any{
		"version":              componentFixtureVersion,
		"file_algorithm":       componentFileAlgorithm,
		"tree_algorithm":       componentTreeAlgorithm,
		"domain_separation":    "the exact ASCII algorithm identifier followed by 0x00",
		"framing":              "uint64be byte length before every variable-length field",
		"tree_entry_kinds":     []any{"D", "F", "L"},
		"tree_order":           "unsigned bytewise order over the UTF-8 relative path",
		"not_hashed":           []any{"acl", "extended-attribute", "mode", "owner", "timestamp"},
		"fixtures":             published,
		"all_digests_distinct": true,
	}
}

// trustedComponents are the mutable trusted components the example
// implementation depends on beyond the parent, supervisor, and worker binaries.
// Each one is a closed cryptographic record whose digest comes from a published
// fixture, sorted by kind then name: an unconstrained string could never
// distinguish two different components.
func trustedComponents() []any {
	return sortComponents([]any{
		component("capability-probe", "capability-probe-suite", componentTreeAlgorithm,
			fixtureDigest("capability-probe-suite")),
		component("enforcement-adapter", "enforcement-backend-adapter", componentFileAlgorithm,
			fixtureDigest("enforcement-backend-adapter")),
	})
}

func component(kind, name, algorithm, digest string) map[string]any {
	return map[string]any{
		"kind": kind, "name": name, "algorithm": algorithm, "content_sha256": digest,
	}
}

// sortComponents keeps the closed component array a sorted unique set by kind
// then name, so a rotation that changes a kind or a name cannot leave the record
// in an order check_tcb_record rejects for the wrong reason.
func sortComponents(components []any) []any {
	sort.SliceStable(components, func(left, right int) bool {
		leftItem := components[left].(map[string]any)
		rightItem := components[right].(map[string]any)
		if leftItem["kind"].(string) != rightItem["kind"].(string) {
			return leftItem["kind"].(string) < rightItem["kind"].(string)
		}
		return leftItem["name"].(string) < rightItem["name"].(string)
	})
	return components
}

// componentNamed finds one component of a record being rotated.
func componentNamed(record map[string]any, name string) map[string]any {
	for _, entry := range record["trusted_components"].([]any) {
		item := entry.(map[string]any)
		if item["name"].(string) == name {
			return item
		}
	}
	panic("unknown trusted component " + name)
}

// tcbFor is the complete hardened-tcb-v1 record for one platform. Every
// identity whose replacement would change what the kernel actually enforces is
// inside it: the manager parent, the supervisor, the worker, every additional
// mutable trusted component, the observed operating system or hypervisor, the
// enforcement backend with its observed version and configuration, and the
// fingerprinted toolchain.
func tcbFor(platform string) map[string]any {
	binding := bindingFor(platform)
	return map[string]any{
		"record_version":      tcbRecordVersion,
		"hardened_profile":    hardenedProfileIdentity,
		"execution_policy":    hardenedExecutionPolicy,
		"platform":            platform,
		"enforcement_backend": binding.backend,
		"backend": map[string]any{
			"version":       binding.backendVersion,
			"configuration": binding.backendConfig,
		},
		"host":               binding.host,
		"parent_sha256":      parentSHA,
		"supervisor_sha256":  supervisorSHA,
		"worker_sha256":      workerSHA,
		"toolchain":          toolchainIdentity(binding.goVersion, toolchainSHA),
		"trusted_components": trustedComponents(),
	}
}

// hardenedTCB is the trusted computing base of the example operation. Its
// platform, host, backend, and toolchain agree with the darwin/arm64 example
// build input, because a hardened native build cannot claim a trusted computing
// base from another host.
func hardenedTCB() map[string]any {
	return tcbFor("macos")
}

// rotatedTCB is the same host after a manager update replaced the worker
// bytes. Everything a package can see is identical, so it isolates the effect
// of the trusted computing base on cache identity.
func rotatedTCB() map[string]any {
	record := hardenedTCB()
	record["worker_sha256"] = updatedWorkerSHA
	return record
}

// linuxTCB backs the conformance-claim example, whose operating system is
// linux.
func linuxTCB() map[string]any {
	return tcbFor("linux")
}

func hardenedBuildRecordV3() map[string]any {
	receipt := validHardenedReceiptV3()
	return map[string]any{
		"driver":                 "go-v1",
		"receipt_schema_version": 3,
		"execution_policy":       hardenedExecutionPolicy,
		"hardened_profile":       hardenedProfileIdentity,
		"tcb":                    hardenedTCB(),
		"cache_key":              receipt["cache_key"],
		"receipt_sha256":         canonicalSHA256(receipt),
		"artifact_sha256":        artifactSHA,
		"artifact_path":          "bin/golden-tool",
	}
}

func portableBuildRecordV1() map[string]any {
	receipt := buildInput(portableExecutionPolicy)
	return map[string]any{
		"driver":                 "go-v1",
		"receipt_schema_version": 1,
		"execution_policy":       portableExecutionPolicy,
		"cache_key":              canonicalSHA256(receipt),
		"receipt_sha256":         canonicalSHA256(receipt),
		"artifact_sha256":        artifactSHA,
		"artifact_path":          "bin/golden-tool",
	}
}

func validHardenedMarkerV4() map[string]any {
	return map[string]any{
		"schema_version":       4,
		"name":                 "golden-skill",
		"source":               "golden-skill",
		"ref_kind":             "revision",
		"ref":                  fixedCommit,
		"commit":               fixedCommit,
		"content_sha256":       buildSourceSHA,
		"locale":               nil,
		"agents":               []any{"codex_cli"},
		"commands":             []any{"golden-tool"},
		"dependencies":         []any{},
		"skill_schema_version": 7,
		"runtime_roots":        []any{"scripts"},
		"build_roots":          []any{"build"},
		"installed_at":         "2000-01-01T00:00:00Z",
		"files":                []any{"SKILL.md"},
		"builds":               map[string]any{"golden-tool": hardenedBuildRecordV3()},
	}
}

func validHardenedClaimV4() map[string]any {
	return map[string]any{
		"schema_version":               4,
		"protocol_version":             hardenedProfileVersion,
		"hardened_profile":             hardenedProfileIdentity,
		"capability_inventory_version": capabilityInventoryVersion,
		"implementation":               "example-manager",
		"implementation_version":       "0.0.0",
		"classes":                      []any{"core", "manager"},
		"suite_sha256":                 externalSHA,
		"portable_suite_sha256":        externalSHA,
		"operating_systems":            []any{"linux"},
		"enforcement_backends": []any{
			map[string]any{
				"operating_system":    "linux",
				"enforcement_backend": "linux-namespace-seccomp-v1",
				// A hardened-backend-version-v1 value in the series this backend
				// declares, so it is comparable with the observed version the
				// claim's own trusted computing base reports.
				"minimum_version": "cgroup2-6.1",
				// Every requirement here must be observed with this exact value
				// in the claim's own trusted computing base, so a claim cannot
				// require a configuration the base it names never had.
				"required_configuration": []any{
					requirement("cgroup.version", "2"),
					requirement("user_namespaces.unprivileged", "enabled"),
				},
			},
		},
		"tcb":        linuxTCB(),
		"guarantees": stringsToAny(guaranteeNames),
		"build_drivers": []any{
			map[string]any{
				"driver": "go-v1", "language": "go",
				"execution_policy":  hardenedExecutionPolicy,
				"hardened_profile":  hardenedProfileIdentity,
				"operating_systems": []any{"linux"},
			},
		},
		"created_at": createdAt,
		"result":     "pass",
	}
}

func writeSchemaCases(suite string) {
	dir := filepath.Join(suite, "schema-cases")
	var index []any
	add := func(schema, name string, valid bool, instance any) {
		caseDir := strings.TrimSuffix(schema, ".schema.json")
		writeJSON(filepath.Join(dir, caseDir, name+".json"), instance)
		index = append(index, map[string]any{
			"schema":   schema,
			"instance": caseDir + "/" + name + ".json",
			"valid":    valid,
		})
	}

	receiptV3 := "hardened-build-receipt-v3.schema.json"
	add(receiptV3, "valid", true, validHardenedReceiptV3())
	add(receiptV3, "invalid-portable-execution-policy", false, withNested(validHardenedReceiptV3(), []string{"input", "policy"}, "execution_policy", portableExecutionPolicy))
	add(receiptV3, "invalid-missing-execution-policy", false, withoutNested(validHardenedReceiptV3(), []string{"input", "policy"}, "execution_policy"))
	add(receiptV3, "invalid-portable-schema-version", false, withField(validHardenedReceiptV3(), "schema_version", 1))
	add(receiptV3, "invalid-unknown-field", false, withField(validHardenedReceiptV3(), "capability_evidence", map[string]any{"record_version": evidenceRecordVersion}))
	add(receiptV3, "invalid-missing-tcb", false, withoutField(validHardenedReceiptV3(), "tcb"))
	add(receiptV3, "invalid-missing-hardened-identity", false, withoutField2(validHardenedReceiptV3(), "input", "hardened"))
	add(receiptV3, "invalid-missing-profile-identity", false, withoutNested(validHardenedReceiptV3(), []string{"input", "hardened"}, "profile"))
	add(receiptV3, "invalid-missing-tcb-digest", false, withoutNested(validHardenedReceiptV3(), []string{"input", "hardened"}, "tcb"))
	add(receiptV3, "invalid-portable-tcb-digest-algorithm", false, withNested(validHardenedReceiptV3(), []string{"input", "hardened", "tcb"}, "algorithm", "curator-build-source-v1"))
	// Completeness of the trusted computing base itself: omitting any member
	// would let two materially different bases share one digest.
	for _, field := range []string{"parent_sha256", "supervisor_sha256", "worker_sha256", "host", "backend", "toolchain", "trusted_components"} {
		add(receiptV3, "invalid-tcb-missing-"+strings.ReplaceAll(field, "_", "-"), false,
			withoutNested(validHardenedReceiptV3(), []string{"tcb"}, field))
	}
	add(receiptV3, "invalid-tcb-untyped-trusted-component", false,
		withNested(validHardenedReceiptV3(), []string{"tcb"}, "trusted_components",
			[]any{"mutable-interpreter-with-no-cryptographic-identity"}))
	add(receiptV3, "invalid-tcb-trusted-component-without-digest", false,
		withNested(validHardenedReceiptV3(), []string{"tcb"}, "trusted_components", []any{
			map[string]any{"kind": "interpreter", "name": "supervisor-launcher-interpreter", "algorithm": "curator-hardened-component-file-v1"},
		}))
	add(receiptV3, "invalid-tcb-unknown-component-kind", false,
		withNested(validHardenedReceiptV3(), []string{"tcb"}, "trusted_components", []any{
			component("anything-at-all", "n", componentFileAlgorithm, fixtureDigest("supervisor-launcher-interpreter")),
		}))
	// review-cycle-3 finding R3-1: a kind that can only ever name one file must
	// not be able to carry a tree digest, and the tree kind must not carry a
	// file digest.
	add(receiptV3, "invalid-tcb-component-tree-algorithm-on-file-kind", false,
		withNested(validHardenedReceiptV3(), []string{"tcb"}, "trusted_components", []any{
			component("interpreter", "supervisor-launcher-interpreter", componentTreeAlgorithm,
				fixtureDigest("capability-probe-suite")),
		}))
	add(receiptV3, "invalid-tcb-component-file-algorithm-on-tree-kind", false,
		withNested(validHardenedReceiptV3(), []string{"tcb"}, "trusted_components", []any{
			component("installed-package-tree", "vendored-runtime", componentFileAlgorithm,
				fixtureDigest("enforcement-backend-adapter")),
		}))
	// review-cycle-3 finding R3-2: the observed host and the backend version
	// series are both bound to the platform the record names.
	add(receiptV3, "invalid-tcb-host-identity-platform-mismatch", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host"}, "identity", "windows-nt"))
	add(receiptV3, "invalid-tcb-host-kind-hypervisor", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host"}, "kind", "hypervisor"))
	add(receiptV3, "invalid-tcb-backend-version-wrong-series", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "backend"}, "version", "cgroup2-6.12"))
	add(receiptV3, "invalid-tcb-backend-version-malformed", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "backend"}, "version", "sandbox-02.0"))
	add(receiptV3, "invalid-tcb-backend-version-without-series", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "backend"}, "version", "2.0"))
	add(receiptV3, "invalid-tcb-reintroduced-string-component-field", false,
		withNested(validHardenedReceiptV3(), []string{"tcb"}, "additional_trusted_components", []any{"mutable-interpreter"}))
	add(receiptV3, "invalid-tcb-platform-backend-mismatch", false,
		withNested(validHardenedReceiptV3(), []string{"tcb"}, "enforcement_backend", "linux-namespace-seccomp-v1"))
	add(receiptV3, "invalid-tcb-host-without-version", false,
		withoutNested(validHardenedReceiptV3(), []string{"tcb", "host"}, "version"))
	// review-cycle-4 finding R4-1: the kernel build identity is required, closed,
	// digested, and written in the grammar the record's own platform declares.
	add(receiptV3, "invalid-tcb-host-build-null", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host"}, "build", nil))
	add(receiptV3, "invalid-tcb-host-build-missing", false,
		withoutNested(validHardenedReceiptV3(), []string{"tcb", "host"}, "build"))
	add(receiptV3, "invalid-tcb-host-build-bare-string", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host"}, "build", "25A123"))
	add(receiptV3, "invalid-tcb-host-build-without-digest", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host"}, "build", map[string]any{
			"algorithm": hostBuildAlgorithm, "identifier": "25A123",
		}))
	add(receiptV3, "invalid-tcb-host-build-unknown-algorithm", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host", "build"}, "algorithm", tcbDigestAlgorithm))
	add(receiptV3, "invalid-tcb-host-build-extra-field", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host", "build"}, "sources", []any{"kern.version"}))
	add(receiptV3, "invalid-tcb-host-build-identifier-platform-mismatch", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host", "build"}, "identifier", linuxBuildID))
	add(receiptV3, "invalid-tcb-host-version-outside-grammar", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host"}, "version", "twenty-five"))
	add(receiptV3, "invalid-tcb-host-version-trailing-newline", false,
		withNested(validHardenedReceiptV3(), []string{"tcb", "host"}, "version", "25.0.0\n"))
	add(receiptV3, "invalid-tcb-backend-without-version", false,
		withoutNested(validHardenedReceiptV3(), []string{"tcb", "backend"}, "version"))
	add(receiptV3, "invalid-tcb-target-platform-mismatch", false,
		withField(validHardenedReceiptV3(), "tcb", tcbFor("linux")))
	add(receiptV3, "invalid-non-hardened-target-platform", false,
		withNested(validHardenedReceiptV3(), []string{"input", "target"}, "goos", "freebsd"))

	receiptV4 := "hardened-build-receipt-v4.schema.json"
	add(receiptV4, "valid", true, validHardenedReceiptV4())
	add(receiptV4, "invalid-portable-execution-policy", false, withNested(validHardenedReceiptV4(), []string{"input", "policy"}, "execution_policy", portableExecutionPolicy))
	add(receiptV4, "invalid-portable-schema-version", false, withField(validHardenedReceiptV4(), "schema_version", 2))
	add(receiptV4, "invalid-unknown-field", false, withField(validHardenedReceiptV4(), "enforcement_backend", "linux-namespace-seccomp-v1"))
	add(receiptV4, "invalid-missing-tcb", false, withoutField(validHardenedReceiptV4(), "tcb"))
	add(receiptV4, "invalid-missing-hardened-identity", false, withoutField2(validHardenedReceiptV4(), "input", "hardened"))
	add(receiptV4, "invalid-tcb-missing-parent-identity", false, withoutNested(validHardenedReceiptV4(), []string{"tcb"}, "parent_sha256"))
	add(receiptV4, "invalid-tcb-missing-host", false, withoutNested(validHardenedReceiptV4(), []string{"tcb"}, "host"))
	add(receiptV4, "invalid-tcb-untyped-trusted-component", false,
		withNested(validHardenedReceiptV4(), []string{"tcb"}, "trusted_components",
			[]any{"mutable-interpreter-with-no-cryptographic-identity"}))
	add(receiptV4, "invalid-tcb-platform-backend-mismatch", false,
		withNested(validHardenedReceiptV4(), []string{"tcb"}, "enforcement_backend", "windows-appcontainer-job-v1"))
	add(receiptV4, "invalid-tcb-target-platform-mismatch", false,
		withField(validHardenedReceiptV4(), "tcb", tcbFor("windows")))
	add(receiptV4, "invalid-tcb-host-build-null", false,
		withNested(validHardenedReceiptV4(), []string{"tcb", "host"}, "build", nil))
	add(receiptV4, "invalid-tcb-host-build-identifier-platform-mismatch", false,
		withNested(validHardenedReceiptV4(), []string{"tcb", "host", "build"}, "identifier", linuxBuildID))

	markerV4 := "hardened-install-marker-v4.schema.json"
	add(markerV4, "valid", true, validHardenedMarkerV4())
	add(markerV4, "invalid-portable-build-record", false, withField(validHardenedMarkerV4(), "builds", map[string]any{"golden-tool": portableBuildRecordV1()}))
	add(markerV4, "invalid-missing-tcb", false, withField(validHardenedMarkerV4(), "builds", map[string]any{"golden-tool": withoutField(hardenedBuildRecordV3(), "tcb")}))
	add(markerV4, "invalid-missing-hardened-profile", false, withField(validHardenedMarkerV4(), "builds", map[string]any{"golden-tool": withoutField(hardenedBuildRecordV3(), "hardened_profile")}))
	add(markerV4, "invalid-portable-schema-version", false, withField(validHardenedMarkerV4(), "schema_version", 3))
	add(markerV4, "invalid-pre-build-skill-schema-version", false, withField(validHardenedMarkerV4(), "skill_schema_version", 5))
	add(markerV4, "invalid-tcb-missing-parent-identity", false, withField(validHardenedMarkerV4(), "builds",
		map[string]any{"golden-tool": withoutNested(hardenedBuildRecordV3(), []string{"tcb"}, "parent_sha256")}))
	add(markerV4, "invalid-tcb-missing-trusted-components", false, withField(validHardenedMarkerV4(), "builds",
		map[string]any{"golden-tool": withoutNested(hardenedBuildRecordV3(), []string{"tcb"}, "trusted_components")}))
	add(markerV4, "invalid-tcb-untyped-trusted-component", false, withField(validHardenedMarkerV4(), "builds",
		map[string]any{"golden-tool": withNested(hardenedBuildRecordV3(), []string{"tcb"}, "trusted_components",
			[]any{"mutable-interpreter-with-no-cryptographic-identity"})}))
	add(markerV4, "invalid-tcb-platform-backend-mismatch", false, withField(validHardenedMarkerV4(), "builds",
		map[string]any{"golden-tool": withNested(hardenedBuildRecordV3(), []string{"tcb"}, "enforcement_backend", "windows-appcontainer-job-v1")}))
	add(markerV4, "invalid-tcb-host-identity-platform-mismatch", false, withField(validHardenedMarkerV4(), "builds",
		map[string]any{"golden-tool": withNested(hardenedBuildRecordV3(), []string{"tcb", "host"}, "identity", "linux")}))
	add(markerV4, "invalid-tcb-component-algorithm-kind-mismatch", false, withField(validHardenedMarkerV4(), "builds",
		map[string]any{"golden-tool": withNested(hardenedBuildRecordV3(), []string{"tcb"}, "trusted_components", []any{
			component("script", "policy-installer", componentTreeAlgorithm, fixtureDigest("capability-probe-suite")),
		})}))
	add(markerV4, "invalid-tcb-host-build-null", false, withField(validHardenedMarkerV4(), "builds",
		map[string]any{"golden-tool": withNested(hardenedBuildRecordV3(), []string{"tcb", "host"}, "build", nil)}))
	add(markerV4, "invalid-tcb-host-build-identifier-platform-mismatch", false, withField(validHardenedMarkerV4(), "builds",
		map[string]any{"golden-tool": withNested(hardenedBuildRecordV3(), []string{"tcb", "host", "build"}, "identifier", linuxBuildID)}))
	add(markerV4, "valid-schema-6-package", true, withField(validHardenedMarkerV4(), "skill_schema_version", 6))

	claimV4 := "hardened-conformance-claim-v4.schema.json"
	add(claimV4, "valid", true, validHardenedClaimV4())
	add(claimV4, "invalid-portable-execution-policy", false, withNestedIndex(validHardenedClaimV4(), "build_drivers", 0, "execution_policy", portableExecutionPolicy))
	add(claimV4, "invalid-portable-protocol-version", false, withField(validHardenedClaimV4(), "protocol_version", portableProtocolVersion))
	add(claimV4, "invalid-missing-hardened-profile", false, withoutField(validHardenedClaimV4(), "hardened_profile"))
	add(claimV4, "invalid-missing-tcb", false, withoutField(validHardenedClaimV4(), "tcb"))
	add(claimV4, "invalid-partial-guarantee-set", false, withField(validHardenedClaimV4(), "guarantees", stringsToAny(guaranteeNames[:5])))
	add(claimV4, "invalid-registry-class", false, withField(validHardenedClaimV4(), "classes", []any{"registry-service"}))
	// The exact adversarial instance review cycle 2 accepted: a macOS trusted
	// computing base carrying a Windows enforcement backend.
	add(claimV4, "invalid-tcb-platform-backend-mismatch", false,
		withNested(withNested(validHardenedClaimV4(), []string{"tcb"}, "platform", "macos"),
			[]string{"tcb"}, "enforcement_backend", "windows-appcontainer-job-v1"))
	add(claimV4, "invalid-backend-operating-system-mismatch", false,
		withNestedIndex(validHardenedClaimV4(), "enforcement_backends", 0, "enforcement_backend", "windows-appcontainer-job-v1"))
	add(claimV4, "invalid-untyped-required-configuration", false,
		withNestedIndex(validHardenedClaimV4(), "enforcement_backends", 0, "required_configuration",
			[]any{"cgroup v2 unified hierarchy"}))
	add(claimV4, "invalid-tcb-missing-host", false, withoutNested(validHardenedClaimV4(), []string{"tcb"}, "host"))
	add(claimV4, "invalid-tcb-missing-parent-identity", false, withoutNested(validHardenedClaimV4(), []string{"tcb"}, "parent_sha256"))
	// The exact adversarial instance review cycle 3 accepted: a linux claim
	// whose own trusted computing base reports a Windows kernel.
	add(claimV4, "invalid-tcb-host-identity-platform-mismatch", false,
		withNested(validHardenedClaimV4(), []string{"tcb", "host"}, "identity", "windows-nt"))
	// review-cycle-4 finding R4-1, in the document that carries a qualification:
	// a claim whose own trusted computing base reports no kernel build identity,
	// or one in a grammar its platform cannot report.
	add(claimV4, "invalid-tcb-host-build-null", false,
		withNested(validHardenedClaimV4(), []string{"tcb", "host"}, "build", nil))
	add(claimV4, "invalid-tcb-host-build-identifier-platform-mismatch", false,
		withNested(validHardenedClaimV4(), []string{"tcb", "host", "build"}, "identifier", "25A123"))
	add(claimV4, "invalid-tcb-host-version-outside-grammar", false,
		withNested(validHardenedClaimV4(), []string{"tcb", "host"}, "version", "6.12.0 "))
	add(claimV4, "invalid-minimum-version-wrong-series", false,
		withNestedIndex(validHardenedClaimV4(), "enforcement_backends", 0, "minimum_version", "sandbox-2.0"))
	add(claimV4, "invalid-minimum-version-malformed", false,
		withNestedIndex(validHardenedClaimV4(), "enforcement_backends", 0, "minimum_version", "cgroup2-06.1"))
	add(claimV4, "invalid-minimum-version-without-series", false,
		withNestedIndex(validHardenedClaimV4(), "enforcement_backends", 0, "minimum_version", "6.1"))

	evidence := "hardened-capability-evidence-v1.schema.json"
	established := evidenceRecord("linux", "linux-namespace-seccomp-v1", "qualified", "established", nil, nil, true)
	rejected := evidenceRecord("linux", "linux-namespace-seccomp-v1", "unqualified", "rejected", "platform-qualification", "hardened_profile_unsupported", false)
	add(evidence, "valid-established", true, established)
	add(evidence, "valid-rejected-unqualified", true, rejected)
	add(evidence, "invalid-available-not-applied", false, withCapabilityEntry(established, 0, "available", "not-applied"))
	add(evidence, "invalid-unprobed-applied", false, withCapabilityEntry(rejected, 0, "unprobed", "applied"))
	add(evidence, "invalid-established-with-unavailable", false, withCapabilityEntry(established, 0, "unavailable", "not-applied"))
	add(evidence, "invalid-missing-capability-entry", false, withoutCapabilityEntry(established, 0))
	add(evidence, "invalid-extra-capability-entry", false, withExtraCapabilityEntry(established))
	add(evidence, "invalid-unknown-capability-class", false, withCapabilityName(established, 0, "no-private-aggregate-domain"))
	add(evidence, "invalid-guarantee-named-as-capability", false, withCapabilityName(established, 0, "total-network-denial"))
	add(evidence, "invalid-rejected-without-diagnostic", false, withField(rejected, "diagnostic", nil))
	add(evidence, "invalid-unknown-record-version", false, withField(established, "record_version", "capability-evidence-v1"))
	add(evidence, "invalid-portable-execution-policy", false, withField(established, "execution_policy", portableExecutionPolicy))
	add(evidence, "invalid-portable-probe-timing", false, withCapabilityProbedAt(established, 0, "pre-worker-launch"))
	add(evidence, "invalid-established-without-qualification", false, withField(established, "qualification_status", "unqualified"))
	add(evidence, "invalid-platform-backend-mismatch", false, withField(rejected, "enforcement_backend", "macos-sandbox-v1"))

	sort.Slice(index, func(left, right int) bool {
		leftItem := index[left].(map[string]any)
		rightItem := index[right].(map[string]any)
		if leftItem["schema"].(string) != rightItem["schema"].(string) {
			return leftItem["schema"].(string) < rightItem["schema"].(string)
		}
		return leftItem["instance"].(string) < rightItem["instance"].(string)
	})
	writeJSON(filepath.Join(dir, "index.json"), index)
}

// -----------------------------------------------------------------------
// manifest and release metadata
// -----------------------------------------------------------------------

func writeManifest(suite string) {
	var lines []string
	must(filepath.WalkDir(suite, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !entry.Type().IsRegular() {
			return nil
		}
		rel, relErr := filepath.Rel(suite, path)
		if relErr != nil {
			return relErr
		}
		rel = filepath.ToSlash(rel)
		if rel == "manifest.json" {
			return nil
		}
		payload, readErr := os.ReadFile(path)
		if readErr != nil {
			return readErr
		}
		sum := sha256.Sum256(payload)
		lines = append(lines, rel+"\tsha256:"+hex.EncodeToString(sum[:]))
		return nil
	}))
	sort.Strings(lines)
	entries := make([]any, 0, len(lines))
	for _, line := range lines {
		parts := strings.SplitN(line, "\t", 2)
		entries = append(entries, map[string]any{"path": parts[0], "sha256": parts[1]})
	}
	writeJSON(filepath.Join(suite, "manifest.json"), map[string]any{
		"profile_version": hardenedProfileVersion,
		"generated_at":    createdAt,
		"generator":       "tools/generate-hardened",
		"files":           entries,
	})
}

func writeReleaseMetadata(root, suite string) {
	hardenedManifest, err := os.ReadFile(filepath.Join(suite, "manifest.json"))
	must(err)
	portableManifest, err := os.ReadFile(filepath.Join(root, "conformance", "v1", "manifest.json"))
	must(err)
	hardenedDigest := sha256.Sum256(hardenedManifest)
	portableDigest := sha256.Sum256(portableManifest)
	hardenedPin := "sha256:" + hex.EncodeToString(hardenedDigest[:])
	portablePin := "sha256:" + hex.EncodeToString(portableDigest[:])

	writeJSON(filepath.Join(root, "release", hardenedProfileVersion+".json"), map[string]any{
		"protocol_version": hardenedProfileVersion,
		"candidate_protocol_pin": map[string]any{
			"manifest_sha256": hardenedPin,
			"suite_root":      "conformance/hardened/v1",
		},
		"portable_baseline": map[string]any{
			"protocol_version": portableProtocolVersion,
			"manifest_sha256":  portablePin,
			"suite_root":       "conformance/v1",
			"modified":         false,
		},
		"downstream_consumption": map[string]any{
			"committed_release_pin_advanced": false,
			"environment":                    "CURATOR_HARDENED_CONFORMANCE_ROOT",
			"required_manifest_sha256":       hardenedPin,
		},
		"execution_policy": map[string]any{
			"hardened":                                   hardenedExecutionPolicy,
			"hardened_profile":                           hardenedProfileIdentity,
			"portable":                                   portableExecutionPolicy,
			"portable_profile_widened":                   false,
			"capability_inventory_version":               capabilityInventoryVersion,
			"capability_evidence_record_version":         evidenceRecordVersion,
			"tcb_record_version":                         tcbRecordVersion,
			"identity_binding_version":                   identityBindingVersion,
			"tcb_digest_algorithm":                       tcbDigestAlgorithm,
			"rc5_reserved_policy_slot_cache_key":         reservedPolicySlotCacheKey,
			"rc5_reserved_policy_slot_is_hardened_input": false,
		},
		"claim_v4": map[string]any{
			"claims_emitted": []any{},
			"linux_status":   "unqualified-pending-native-evidence",
			"macos_status":   "unqualified-pending-native-evidence",
			"windows_status": "unqualified-pending-native-evidence",
		},
		"qualified_platforms":    []any{},
		"owner_story":            ownerStory,
		"specifying_task":        specifyingTask,
		"verification_task":      verificationTask,
		"created_at":             createdAt,
		"source_baseline_commit": sourceBaselineCommit,
	})
}

// -----------------------------------------------------------------------
// helpers
// -----------------------------------------------------------------------

func withField(object map[string]any, field string, value any) map[string]any {
	clone := deepClone(object)
	clone[field] = value
	return clone
}

func withoutField(object map[string]any, field string) map[string]any {
	clone := deepClone(object)
	delete(clone, field)
	return clone
}

// withoutField2 drops a field from one nested object.
func withoutField2(object map[string]any, parent, field string) map[string]any {
	clone := deepClone(object)
	delete(clone[parent].(map[string]any), field)
	return clone
}

func withNested(object map[string]any, path []string, field string, value any) map[string]any {
	clone := deepClone(object)
	cursor := clone
	for _, step := range path {
		cursor = cursor[step].(map[string]any)
	}
	cursor[field] = value
	return clone
}

func withoutNested(object map[string]any, path []string, field string) map[string]any {
	clone := deepClone(object)
	cursor := clone
	for _, step := range path {
		cursor = cursor[step].(map[string]any)
	}
	delete(cursor, field)
	return clone
}

func withNestedIndex(object map[string]any, field string, index int, key string, value any) map[string]any {
	clone := deepClone(object)
	list := clone[field].([]any)
	item := list[index].(map[string]any)
	item[key] = value
	return clone
}

func withCapabilityEntry(record map[string]any, index int, availability, status string) map[string]any {
	clone := deepClone(record)
	entry := clone["capabilities"].([]any)[index].(map[string]any)
	entry["availability"] = availability
	entry["status"] = status
	return clone
}

func withCapabilityName(record map[string]any, index int, name string) map[string]any {
	clone := deepClone(record)
	clone["capabilities"].([]any)[index].(map[string]any)["name"] = name
	return clone
}

func withCapabilityProbedAt(record map[string]any, index int, probedAt string) map[string]any {
	clone := deepClone(record)
	clone["capabilities"].([]any)[index].(map[string]any)["probed_at"] = probedAt
	return clone
}

func withoutCapabilityEntry(record map[string]any, index int) map[string]any {
	clone := deepClone(record)
	list := clone["capabilities"].([]any)
	clone["capabilities"] = append(append([]any{}, list[:index]...), list[index+1:]...)
	return clone
}

func withExtraCapabilityEntry(record map[string]any) map[string]any {
	clone := deepClone(record)
	list := clone["capabilities"].([]any)
	extra := deepClone(list[0].(map[string]any))
	clone["capabilities"] = append(append([]any{}, list...), extra)
	return clone
}

func deepClone(value map[string]any) map[string]any {
	out := make(map[string]any, len(value))
	for key, item := range value {
		out[key] = deepCloneValue(item)
	}
	return out
}

func deepCloneValue(value any) any {
	switch typed := value.(type) {
	case map[string]any:
		return deepClone(typed)
	case []any:
		out := make([]any, 0, len(typed))
		for _, item := range typed {
			out = append(out, deepCloneValue(item))
		}
		return out
	default:
		return value
	}
}

func stringsToAny(values []string) []any {
	out := make([]any, 0, len(values))
	for _, value := range values {
		out = append(out, value)
	}
	return out
}

func canonicalSHA256(value any) string {
	digest := sha256.Sum256(canonicalValue(value))
	return "sha256:" + hex.EncodeToString(digest[:])
}

func canonicalValue(value any) []byte {
	switch typed := value.(type) {
	case map[string]any:
		keys := make([]string, 0, len(typed))
		for key := range typed {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		var out strings.Builder
		out.WriteByte('{')
		for index, key := range keys {
			if index > 0 {
				out.WriteByte(',')
			}
			out.Write(canonicalString(key))
			out.WriteByte(':')
			out.Write(canonicalValue(typed[key]))
		}
		out.WriteByte('}')
		return []byte(out.String())
	case []any:
		var out strings.Builder
		out.WriteByte('[')
		for index, item := range typed {
			if index > 0 {
				out.WriteByte(',')
			}
			out.Write(canonicalValue(item))
		}
		out.WriteByte(']')
		return []byte(out.String())
	case string:
		return canonicalString(typed)
	case bool:
		if typed {
			return []byte("true")
		}
		return []byte("false")
	case int:
		return []byte(fmt.Sprintf("%d", typed))
	case nil:
		return []byte("null")
	default:
		panic(fmt.Sprintf("unsupported canonical value %T", value))
	}
}

func canonicalString(value string) []byte {
	if !utf8.ValidString(value) {
		panic("invalid UTF-8")
	}
	var out strings.Builder
	out.WriteByte('"')
	for _, r := range value {
		switch r {
		case '"':
			out.WriteString(`\"`)
		case '\\':
			out.WriteString(`\\`)
		case '\b':
			out.WriteString(`\b`)
		case '\f':
			out.WriteString(`\f`)
		case '\n':
			out.WriteString(`\n`)
		case '\r':
			out.WriteString(`\r`)
		case '\t':
			out.WriteString(`\t`)
		default:
			if r < 0x20 {
				fmt.Fprintf(&out, `\u%04x`, r)
			} else {
				out.WriteRune(r)
			}
		}
	}
	out.WriteByte('"')
	return []byte(out.String())
}

func writeJSON(path string, value any) {
	must(os.MkdirAll(filepath.Dir(path), 0o755))
	file, err := os.Create(path)
	must(err)
	encoder := json.NewEncoder(file)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	must(encoder.Encode(value))
	must(file.Close())
}

func must(err error) {
	if err != nil {
		panic(fmt.Sprintf("generate hardened conformance suite: %v", err))
	}
}
