package main

// Toolchain requirement, preflight, guidance and Go-metadata vectors.
//
// The normative contract is decisions/0007-compiled-build-toolchain-preflight.md
// and its reference docs/compiled-build-toolchain-requirements.md. Every case
// below carries the manager's compatibility set and, where the outcome depends
// on it, the resolved version as fixture input, so a conforming manager reaches
// the same verdict on a runner that has no toolchain of that language at all.

import (
	"path/filepath"
)

const (
	// goToolchainFingerprint is the frozen rc.4 Go toolchain fingerprint
	// algorithm. Adopting the requirement contract does not re-version it.
	goToolchainFingerprint = "curator-go-toolchain-v1"
	// goBaselineVersion is the registry baseline every schema-6 and schema-7
	// command inherits, which is why those schemas gain two-stage preflight
	// without gaining a field.
	goBaselineVersion = "1.23.0"
	// goResolvedVersion is the fixture host toolchain for every case that does
	// not declare its own.
	goResolvedVersion = "1.23.4"
	// guidanceCatalogVersion is the catalog version this protocol surface
	// publishes. A published version is immutable in whole.
	guidanceCatalogVersion = 1
)

// atLeast, rangeOf and exactly build the three closed requirement kinds.
func atLeast(min string) map[string]any {
	return map[string]any{"kind": "at_least", "min": min}
}

func rangeOf(min, below string) map[string]any {
	return map[string]any{"kind": "range", "min": min, "below": below}
}

func exactly(equals string) map[string]any {
	return map[string]any{"kind": "exact", "equals": equals}
}

func requirement(id string, version map[string]any) map[string]any {
	return map[string]any{"id": id, "version": version}
}

// interval renders an effective requirement. An empty upper bound means +inf.
func interval(min string, max string, maxInclusive bool) map[string]any {
	value := map[string]any{"min": min, "min_inclusive": true}
	if max != "" {
		value["max"] = max
		value["max_inclusive"] = maxInclusive
	}
	return value
}

func platform(operatingSystem, architecture string) map[string]any {
	return map[string]any{"operating_system": operatingSystem, "architecture": architecture}
}

func goPlatforms() []any {
	return []any{
		platform("linux", "amd64"), platform("linux", "arm64"),
		platform("macos", "amd64"), platform("macos", "arm64"),
		platform("windows", "amd64"), platform("windows", "arm64"),
	}
}

func goCompatibility() map[string]any {
	return map[string]any{
		"family_granularity": "major_minor",
		"families":           []any{[]any{1, 23}},
	}
}

func probeVector(name string, argv ...string) map[string]any {
	values := make([]any, 0, len(argv))
	for _, item := range argv {
		values = append(values, item)
	}
	return map[string]any{"name": name, "argv": values}
}

// goProbeVectors are the existing protocol/core.md section 4.2 bootstrap
// vectors, expressed as the argument vectors appended to the entry's resolved
// primary executable. The entry adds no process invocation.
func goProbeVectors() []any {
	return []any{
		probeVector("telemetry", "telemetry", "off"),
		probeVector("version", "version"),
		probeVector("env", "env", "-json", "GOROOT", "GOHOSTOS", "GOHOSTARCH", "GOOS",
			"GOARCH", "GO386", "GOAMD64", "GOARM", "GOARM64", "GOMIPS", "GOMIPS64",
			"GOPPC64", "GORISCV64", "GOWASM", "GOTELEMETRY", "GOTELEMETRYDIR"),
	}
}

// valueClass declares a class that matches a byte string. absenceClass declares
// the one class that matches the field not being present at all: it classifies
// no value, which is why the section 3.1.1 forbidden-before-compared precedence
// is stated over value classes and this one may precede them.
func valueClass(name, disposition, outcome string) map[string]any {
	return map[string]any{
		"name": name, "matches": "value",
		"disposition": disposition, "outcome": outcome,
	}
}

func absenceClass() map[string]any {
	return map[string]any{
		"name": "absent", "matches": "absence",
		"disposition": "ignored", "outcome": "no_assertion",
	}
}

func catchAllClass(name, disposition, outcome string) map[string]any {
	class := valueClass(name, disposition, outcome)
	class["catch_all"] = true
	return class
}

// goMetadataSources is the closed two-directive disposition table of the `go`
// entry. Both directives carry a value classifier, so each records `classified`
// and its effective disposition for a value is that of the matched class.
func goMetadataSources() []any {
	return []any{
		map[string]any{
			"path": "go.mod",
			"fields": []any{
				map[string]any{
					"field_path":  "go",
					"disposition": "classified",
					"classes": []any{
						absenceClass(),
						valueClass("release-literal", "compared", "compare_base_triple"),
						valueClass("prerelease-literal", "compared", "compare_base_triple"),
						catchAllClass("unclassifiable", "compared", "unclassifiable"),
					},
				},
				map[string]any{
					"field_path":  "toolchain",
					"disposition": "classified",
					"classes": []any{
						absenceClass(),
						valueClass("path-bearing-name", "forbidden", "package_influence_forbidden"),
						valueClass("custom-distribution-name", "forbidden", "package_influence_forbidden"),
						valueClass("default", "compared", "permitted_not_honored"),
						valueClass("release-name", "compared", "compare_base_triple"),
						valueClass("prerelease-name", "compared", "compare_base_triple"),
						catchAllClass("unclassifiable", "compared", "unclassifiable"),
					},
				},
			},
		},
	}
}

// expectedRustMetadataSources is the disposition table TASK-260728-12pnm1 MUST
// confirm or correct on a qualified host. It is an expectation attached to a
// reserved entry, never an admission: no driver of that language exists, and
// the entry stays `reserved` until its own decision completes every field of
// section 1.1.
func expectedRustMetadataSources() []any {
	return []any{
		map[string]any{
			"path": "rust-toolchain.toml",
			"fields": []any{
				map[string]any{"field_path": "toolchain.path", "disposition": "forbidden"},
				map[string]any{
					"field_path":  "toolchain.channel",
					"disposition": "classified",
					"classes": []any{
						absenceClass(),
						valueClass("release-track", "compared", "permitted_not_honored"),
						valueClass("prerelease-track", "compared", "unclassifiable"),
						valueClass("version-literal", "compared", "compare_base_triple"),
						catchAllClass("unclassifiable", "compared", "unclassifiable"),
					},
				},
			},
		},
		map[string]any{
			"path": "Cargo.toml",
			"fields": []any{
				map[string]any{"field_path": "package.rust-version", "disposition": "compared"},
				map[string]any{"field_path": "workspace.package.rust-version", "disposition": "compared"},
			},
		},
	}
}

func reservedRegistryEntry(id, owner string, companions []any, expected []any) map[string]any {
	entry := map[string]any{"toolchain_id": id, "status": "reserved", "owner": owner}
	if companions != nil {
		entry["companions"] = companions
	}
	if expected != nil {
		entry["expected_metadata_sources"] = expected
	}
	return entry
}

// toolchainRegistry is the manager-owned `toolchain-registry-v1` document. It
// is the only mapping from a driver to a toolchain and is never derived from a
// driver name, a language name, a file extension, or package data.
func toolchainRegistry() map[string]any {
	return map[string]any{
		"schema_version": 1,
		"entries": []any{
			map[string]any{
				"toolchain_id": "go",
				"status":       "complete",
				"drivers":      []any{"go-v1", "go-repository-v1"},
				"companions":   []any{},
				"platforms":    goPlatforms(),
				"primary_relpath": map[string]any{
					"linux": "bin/go", "macos": "bin/go", "windows": "bin/go.exe",
				},
				"probe": map[string]any{
					"linux": goProbeVectors(), "macos": goProbeVectors(), "windows": goProbeVectors(),
				},
				"normalization": map[string]any{
					"probe":            "version",
					"stream":           "stdout",
					"field_separator":  "space",
					"field_index":      2,
					"anchored":         true,
					"pattern":          `^go(\d+)\.(\d+)(?:\.(\d+))?(.*)$`,
					"absent_patch":     "0",
					"prerelease_group": 4,
					"max_output_bytes": 65536,
				},
				"fingerprint_algorithm": goToolchainFingerprint,
				"baseline":              atLeast(goBaselineVersion),
				"compatibility":         goCompatibility(),
				"metadata_sources":      goMetadataSources(),
			},
			reservedRegistryEntry("jdk", "TASK-260728-168smo", nil, nil),
			reservedRegistryEntry("kotlin", "TASK-260728-168smo", []any{"jdk"}, nil),
			reservedRegistryEntry("rust", "TASK-260728-12pnm1", []any{}, expectedRustMetadataSources()),
			reservedRegistryEntry("swift", "TASK-260728-1yhuqi", nil, nil),
		},
	}
}

// toolchainReasons is the total code-to-reason mapping of section 6.1. The
// mapping is the identity on the `build_toolchain_` suffix, so it cannot drift
// as codes are added.
var toolchainReasons = []struct {
	code  string
	class string
}{
	{"changed", "configuration"},
	{"incompatible", "host"},
	{"metadata_mismatch", "host"},
	{"package_influence_forbidden", "authoring"},
	{"platform_unsupported", "host"},
	{"prerelease_unsupported", "host"},
	{"requirement_invalid", "authoring"},
	{"requirement_unsatisfiable", "authoring"},
	{"untested_release", "host"},
	{"untrusted", "configuration"},
	{"unavailable", "host"},
	{"version_undetermined", "host"},
}

const (
	hostGuidanceOrigin          = "https://go.dev/doc/install"
	hostToolchainGuidanceOrigin = "https://go.dev/doc/toolchain"
	configurationOrigin         = "https://relux-works.github.io/curator/operator/toolchains"
	authoringOrigin             = "https://relux-works.github.io/curator-spec/protocol/core.html#toolchain-requirements"
)

func guidanceOrigin(class, reason string) string {
	switch class {
	case "configuration":
		return configurationOrigin
	case "authoring":
		return authoringOrigin
	}
	if reason == "metadata_mismatch" {
		return hostToolchainGuidanceOrigin
	}
	return hostGuidanceOrigin
}

func guidanceID(toolchain, reason, guidancePlatform string, revision int) string {
	return "toolchain." + toolchain + "." + reason + "." + guidancePlatform + ".r" + itoa(revision)
}

func itoa(value int) string {
	if value == 0 {
		return "0"
	}
	digits := ""
	for value > 0 {
		digits = string(rune('0'+value%10)) + digits
		value /= 10
	}
	return digits
}

func guidanceEntry(toolchain, reason, guidancePlatform, class string, revision int, summary string, active bool, supersededBy string) map[string]any {
	entry := map[string]any{
		"guidance_id":    guidanceID(toolchain, reason, guidancePlatform, revision),
		"toolchain_id":   toolchain,
		"reason":         reason,
		"platform":       guidancePlatform,
		"guidance_class": class,
		"primary_source": guidanceOrigin(class, reason),
		"summary":        summary,
		"active":         active,
	}
	if supersededBy != "" {
		entry["superseded_by"] = supersededBy
	}
	return entry
}

// guidanceCatalog is total over the supported toolchains, all twelve reasons
// and the supported platforms. A supported toolchain is one with a complete
// registry entry, so `go` is the only one the coverage gate demands rows for.
//
// The three coverage modes of section 6.3 are all exercised, because all three
// are valid and the gate must accept each: `unavailable` is `per_os`,
// `untrusted` is hybrid — one `any` fallback plus a Windows override — and
// every other reason is `any`. `untrusted` additionally carries the retired
// revision 1 of its Windows tuple, so a superseded entry stays resolvable while
// selection returns revision 2.
func guidanceCatalog() map[string]any {
	var entries []any
	for _, reason := range toolchainReasons {
		switch reason.code {
		case "unavailable":
			for _, operatingSystem := range []string{"linux", "macos", "windows"} {
				entries = append(entries, guidanceEntry("go", reason.code, operatingSystem, reason.class, 1,
					"Install a manager-trusted Go release and declare its root in operator configuration.", true, ""))
			}
		case "untrusted":
			entries = append(entries, guidanceEntry("go", reason.code, "any", reason.class, 1,
				"Point the operator toolchain configuration at a concrete toolchain root.", true, ""))
			entries = append(entries, guidanceEntry("go", reason.code, "windows", reason.class, 1,
				"Point the operator toolchain configuration at a concrete toolchain root.", false,
				guidanceID("go", reason.code, "windows", 2)))
			entries = append(entries, guidanceEntry("go", reason.code, "windows", reason.class, 2,
				"Point the operator toolchain configuration at a concrete toolchain root, not a launcher on PATH.", true, ""))
		default:
			entries = append(entries, guidanceEntry("go", reason.code, "any", reason.class, 1,
				"See the primary source for this reason.", true, ""))
		}
	}
	return map[string]any{
		"schema_version":  1,
		"catalog_version": guidanceCatalogVersion,
		"entries":         entries,
	}
}

func sourceRef(surface, location string) map[string]any {
	return map[string]any{"surface": surface, "location": location}
}

// writeToolchainVectors emits every toolchain vector file.
func writeToolchainVectors(dir string) {
	registry := toolchainRegistry()
	catalog := guidanceCatalog()
	writeJSON(filepath.Join(dir, "toolchain-registry.json"), map[string]any{
		"registry": registry,
		"cases":    toolchainRegistryCases(),
	})
	writeJSON(filepath.Join(dir, "toolchain-guidance-catalog.json"), map[string]any{
		"catalog":     catalog,
		"reasons":     guidanceReasonRows(),
		"cases":       guidanceCases(),
		"transitions": guidanceTransitionCases(),
	})
	writeJSON(filepath.Join(dir, "toolchain-preflight.json"), map[string]any{
		"defaults": map[string]any{
			"driver":            "go-v1",
			"toolchain_id":      "go",
			"compatibility":     goCompatibility(),
			"host_platform":     platform("macos", "arm64"),
			"resolved_version":  goResolvedVersion,
			"prerelease":        false,
			"reported_target":   "darwin/arm64",
			"native_target":     "darwin/arm64",
			"declaration":       declaration("operator_config", "concrete_root"),
			"registry_baseline": atLeast(goBaselineVersion),
		},
		"cases": preflightCases(),
	})
	writeJSON(filepath.Join(dir, "toolchain-go-metadata.json"), map[string]any{
		"grammars":                    goGrammars(),
		"go_directive_classes":        goDirectiveClasses(),
		"toolchain_directive_classes": toolchainDirectiveClasses(),
		"cases":                       goMetadataCases(),
		"alignment":                   goAlignmentTable(),
		"probe":                       boundaryProbeContract(),
	})
	writeJSON(filepath.Join(dir, "toolchain-diagnostics.json"), map[string]any{
		"sites": diagnosticSites(),
		// Every payload instance the union admits, one per declared firing
		// site. The inventory cases below name the shapes the reference calls
		// out; `union` is what proves the site table is exhausted.
		"union":    mapsToAny(diagnosticPayloads()),
		"payloads": diagnosticPayloadCases(),
	})
}
