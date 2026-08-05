package main

// Diagnostic payload vectors: inventory cases 65 through 71.
//
// The payload is a discriminated union keyed by the firing site, because a
// payload carries exactly the values established at the site where it fires and
// every stage's steps are totally ordered. Nothing is optional-by-judgment and
// there are no sentinels.

func site(code, stage, step string, discriminant map[string]any, effective, resolved bool) map[string]any {
	value := map[string]any{
		"code": code, "stage": stage, "step": step,
		"effective_requirement": effective,
		"resolved_version":      resolved,
		"prerelease":            resolved,
	}
	if discriminant != nil {
		value["discriminant"] = discriminant
	}
	return value
}

// diagnosticSites is the section 5.1 site table. `effective_requirement` is
// absent at exactly the three sites whose own interval computation had not
// produced an interval, and `resolved_version` at exactly the seven sites that
// precede normalization.
func diagnosticSites() []any {
	return []any{
		site("build_toolchain_requirement_invalid", "validation", "validation", nil, false, false),
		site("build_toolchain_requirement_unsatisfiable", "validation", "validation", nil, false, false),
		site("build_toolchain_requirement_unsatisfiable", "B", "1", nil, false, true),
		site("build_toolchain_unavailable", "A", "3a", nil, true, false),
		site("build_toolchain_untrusted", "A", "3b", map[string]any{"substep": "origin"}, true, false),
		site("build_toolchain_untrusted", "A", "3c", map[string]any{"substep": "shape"}, true, false),
		site("build_toolchain_version_undetermined", "A", "4", nil, true, false),
		site("build_toolchain_platform_unsupported", "A", "2", map[string]any{"check": "host_pair"}, true, false),
		site("build_toolchain_platform_unsupported", "A", "6", map[string]any{"check": "native_target"}, true, true),
		site("build_toolchain_prerelease_unsupported", "A", "5", nil, true, true),
		site("build_toolchain_incompatible", "A", "7", nil, true, true),
		site("build_toolchain_incompatible", "B", "2", nil, true, true),
		site("build_toolchain_untested_release", "A", "8", nil, true, true),
		site("build_toolchain_metadata_mismatch", "B", "3", nil, true, true),
		site("build_toolchain_metadata_mismatch", "B", "5", nil, true, true),
		site("build_toolchain_package_influence_forbidden", "B", "4", nil, true, true),
		site("build_toolchain_changed", "A", "fingerprint", nil, true, true),
		site("build_toolchain_changed", "publication", "publication", nil, true, true),
	}
}

func toolchainIdentity(version, sum string) map[string]any {
	return map[string]any{
		"algorithm":       goToolchainFingerprint,
		"version":         version,
		"primary_relpath": "bin/go",
		"content_sha256":  "sha256:" + sum,
	}
}

func payloadCase(id, name string, payload map[string]any, assertions map[string]any) map[string]any {
	return map[string]any{
		"case": id, "name": name, "payloads": []any{payload}, "asserts": assertions,
	}
}

// splitPayloadCase carries the two payload shapes of one inventory case whose
// code has two representable forms: a derived canonical assertion versus the
// unclassifiable token, and the origin versus shape sub-steps.
func splitPayloadCase(id, name string, first, second map[string]any, assertions map[string]any) map[string]any {
	return map[string]any{
		"case": id, "name": name, "payloads": []any{first, second}, "asserts": assertions,
	}
}

// diagnosticPayloads returns every payload instance in inventory order. Each is
// a real instance of `toolchain-diagnostic-v1.schema.json`, so the union is
// exercised by the compiled validator rather than described in prose.
func diagnosticPayloads() []map[string]any {
	baseline := interval(goBaselineVersion, "", false)
	manifestRef := sourceRef("manifest", "/commands/build-tool/toolchain")
	descriptorRef := sourceRef("descriptor", "/targets/golden-tool/toolchain")
	registryRef := sourceRef("registry", "go")
	return []map[string]any{
		{
			"code": "build_toolchain_requirement_invalid", "stage": "validation",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id": guidanceID("go", "requirement_invalid", "any", 1),
			"source_ref":  manifestRef, "violation": "version_literal_malformed",
		},
		{
			"code": "build_toolchain_requirement_unsatisfiable", "stage": "validation",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id": guidanceID("go", "requirement_unsatisfiable", "any", 1),
			"fragments": []any{
				map[string]any{"source_ref": registryRef, "requirement": atLeast(goBaselineVersion)},
				map[string]any{"source_ref": manifestRef, "requirement": rangeOf("1.20.0", "1.22.0")},
			},
			"conflict": map[string]any{
				"lower_bound": goBaselineVersion, "lower_sources": []any{"registry_baseline"},
				"upper_bound": "1.22.0", "upper_sources": []any{manifestRef},
				"upper_inclusive": false,
			},
		},
		{
			"code": "build_toolchain_unavailable", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "unavailable", "macos", 1),
			"effective_requirement": baseline,
		},
		{
			"code": "build_toolchain_prerelease_unsupported", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "prerelease_unsupported", "any", 1),
			"effective_requirement": baseline,
			"resolved_version":      "1.24.0", "prerelease": true,
		},
		{
			"code": "build_toolchain_untested_release", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "untested_release", "any", 1),
			"effective_requirement": baseline,
			"resolved_version":      "1.99.0", "prerelease": false,
			"admitted_families": []any{[]any{1, 23}},
		},
		{
			"code": "build_toolchain_metadata_mismatch", "stage": "B",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "metadata_mismatch", "any", 1),
			"effective_requirement": baseline,
			"resolved_version":      goResolvedVersion, "prerelease": false,
			"source_ref": sourceRef("source_metadata", "go.mod#go"),
			"assertion":  atLeast("1.24.0"),
		},
		{
			"code": "build_toolchain_metadata_mismatch", "stage": "B",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "metadata_mismatch", "any", 1),
			"effective_requirement": baseline,
			"resolved_version":      goResolvedVersion, "prerelease": false,
			"source_ref": sourceRef("source_metadata", "go.mod#toolchain"),
			"assertion":  "unclassifiable",
		},
		{
			"code": "build_toolchain_untrusted", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "untrusted", "any", 1),
			"effective_requirement": baseline,
			"substep":               "origin", "origin_class": "ambient_path",
		},
		{
			"code": "build_toolchain_untrusted", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "untrusted", "windows", 2),
			"effective_requirement": baseline,
			"substep":               "shape",
		},
		{
			"code": "build_toolchain_requirement_unsatisfiable", "stage": "B",
			"driver": "go-repository-v1", "toolchain_id": "go",
			"guidance_id": guidanceID("go", "requirement_unsatisfiable", "any", 1),
			"fragments": []any{
				map[string]any{"source_ref": registryRef, "requirement": atLeast(goBaselineVersion)},
				map[string]any{"source_ref": sourceRef("manifest", "/commands/golden-tool/toolchain"), "requirement": rangeOf("1.23.0", "1.25.0")},
				map[string]any{"source_ref": descriptorRef, "requirement": exactly("1.26.0")},
			},
			"conflict": map[string]any{
				"lower_bound": "1.26.0", "lower_sources": []any{descriptorRef},
				"upper_bound":     "1.25.0",
				"upper_sources":   []any{sourceRef("manifest", "/commands/golden-tool/toolchain")},
				"upper_inclusive": false,
			},
			"resolved_version": goResolvedVersion, "prerelease": false,
		},
		{
			"code": "build_toolchain_platform_unsupported", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "platform_unsupported", "any", 1),
			"effective_requirement": baseline,
			"check":                 "host_pair",
			"host_platform":         platform("linux", "arm64"),
			"supported_platforms":   goPlatforms(),
		},
		{
			"code": "build_toolchain_platform_unsupported", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "platform_unsupported", "any", 1),
			"effective_requirement": baseline,
			"check":                 "native_target",
			"host_platform":         platform("macos", "arm64"),
			"reported_target":       "linux/amd64", "native_target": "darwin/arm64",
			"resolved_version": goResolvedVersion, "prerelease": false,
		},
		{
			"code": "build_toolchain_incompatible", "stage": "B",
			"driver": "go-repository-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "incompatible", "any", 1),
			"effective_requirement": interval("1.24.0", "", false),
			"resolved_version":      "1.23.0", "prerelease": false,
		},
		{
			"code": "build_toolchain_version_undetermined", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "version_undetermined", "any", 1),
			"effective_requirement": baseline,
			"probe":                 "version", "reason": "unmatched",
		},
		{
			"code": "build_toolchain_package_influence_forbidden", "stage": "B",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "package_influence_forbidden", "any", 1),
			"effective_requirement": baseline,
			"resolved_version":      goResolvedVersion, "prerelease": false,
			"source_ref":  sourceRef("source_metadata", "go.mod#toolchain"),
			"value_class": "custom-distribution-name",
		},
		{
			"code": "build_toolchain_changed", "stage": "publication",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "changed", "any", 1),
			"effective_requirement": baseline,
			"resolved_version":      goResolvedVersion, "prerelease": false,
			"identity_before": toolchainIdentity(goResolvedVersion, repeatChar("a", 64)),
			"identity_after":  toolchainIdentity(goResolvedVersion, repeatChar("b", 64)),
		},
		{
			"code": "build_toolchain_incompatible", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "incompatible", "any", 1),
			"effective_requirement": interval("1.23.4", "", false),
			"resolved_version":      "1.23.0", "prerelease": false,
		},
		{
			"code": "build_toolchain_changed", "stage": "A",
			"driver": "go-v1", "toolchain_id": "go",
			"guidance_id":           guidanceID("go", "changed", "any", 1),
			"effective_requirement": baseline,
			"resolved_version":      goResolvedVersion, "prerelease": false,
			"identity_before": toolchainIdentity(goResolvedVersion, repeatChar("c", 64)),
			"identity_after":  toolchainIdentity(goResolvedVersion, repeatChar("d", 64)),
		},
	}
}

func repeatChar(value string, count int) string {
	result := ""
	for index := 0; index < count; index++ {
		result += value
	}
	return result
}

func diagnosticPayloadCases() []any {
	payloads := diagnosticPayloads()
	return []any{
		payloadCase("65", "requirement-invalid-carries-a-location-and-a-closed-violation-token",
			payloads[0], map[string]any{
				"carries":      []any{"source_ref", "violation"},
				"absent":       []any{"effective_requirement", "resolved_version", "prerelease"},
				"value_echoed": false,
				"note":         "the payload never reproduces an unvalidated package byte",
			}),
		payloadCase("66", "requirement-unsatisfiable-carries-validated-fragments-and-the-conflicting-bounds",
			payloads[1], map[string]any{
				"carries":                         []any{"fragments", "conflict"},
				"absent":                          []any{"effective_requirement"},
				"fragments_validated":             true,
				"byte_identical_under_reorder":    true,
				"sources_in_unicode_scalar_order": true,
			}),
		payloadCase("67", "unavailable-carries-the-effective-requirement-and-no-resolved-version",
			payloads[2], map[string]any{
				"carries": []any{"effective_requirement"},
				"absent":  []any{"resolved_version", "prerelease"},
			}),
		payloadCase("68", "prerelease-unsupported-carries-the-resolved-version-and-the-prerelease-flag",
			payloads[3], map[string]any{"carries": []any{"resolved_version", "prerelease"}}),
		payloadCase("69", "untested-release-carries-the-admitted-families",
			payloads[4], map[string]any{"carries": []any{"admitted_families"}}),
		splitPayloadCase("70", "metadata-mismatch-carries-a-source-ref-plus-a-derived-assertion-or-the-unclassifiable-token",
			payloads[5], payloads[6], map[string]any{
				"carries":         []any{"source_ref", "assertion"},
				"assertion_kinds": []any{"derived", "unclassifiable"},
				"note":            "always unclassifiable at the B step 3 file-shape site, because no value was classified",
			}),
		splitPayloadCase("71", "untrusted-carries-substep-and-origin-class-exactly-for-the-origin-sub-step",
			payloads[7], payloads[8], map[string]any{
				"carries":                  []any{"substep"},
				"origin_class_present_for": []any{"origin"},
				"origin_class_absent_for":  []any{"shape"},
			}),
	}
}
