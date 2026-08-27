package main

// Schema cases for the surfaces the toolchain contract mints: manifest schema 8,
// descriptor schema 2, the manager-owned registry and guidance catalog, and the
// diagnostic payload union.
//
// Inventory cases 27 and 28 live here rather than in the toolchain suite,
// because a field outside the closed set never reaches a `build_toolchain_*`
// code: it is the existing schema rejection that protocol/core.md section 4
// already requires of every wire object.

// forbiddenWireFieldNames are the field kinds no manifest build command and no
// descriptor target may ever carry. The release gate enumerates the published
// property names and fails on one of these; the cases below prove the shipped
// schemas reject an instance carrying one.
var forbiddenWireFieldNames = []struct {
	field string
	value any
}{
	{"toolchain_path", "/usr/local/go/bin/go"},
	{"toolchain_root", "/usr/local/go"},
	{"download_url", "https://example.test/go.tgz"},
	{"mirror", "https://mirror.example.test/go"},
	{"channel", "nightly"},
	{"track", "beta"},
	{"version_manager", "rustup"},
	{"install_command", "brew install go"},
	{"package_manager", "brew"},
	{"env", map[string]any{"GOROOT": "/opt/go"}},
	{"path", "/opt/go/bin"},
	{"credentials", "token"},
	{"keyring", "login"},
	{"checksum", "sha256:" + repeatChar("0", 64)},
	{"trust_root", "https://example.test/roots.pem"},
}

func validV8SkillManifest() map[string]any {
	return map[string]any{
		"schema_version": 8,
		"capabilities":   map[string]any{},
		"build_roots":    []any{"build"},
		"build_repositories": map[string]any{
			"golden-tools": map[string]any{
				"git":           "https://github.com/example/golden-tools.git",
				"locked_commit": map[string]any{"object_format": "sha1", "hex": fixedCommit},
				"tag":           "v1.4.0",
			},
		},
		"commands": map[string]any{
			"build-tool": map[string]any{
				"type": "build", "driver": "go-v1", "source_dir": "build/cmd/tool",
				"toolchain": requirement("go", atLeast(goBaselineVersion)),
			},
			"golden-tool": map[string]any{
				"type": "build", "driver": "go-repository-v1",
				"repository": "golden-tools", "target": "golden-tool",
				"toolchain": requirement("go", rangeOf(goBaselineVersion, "1.25.0")),
			},
			"script-tool": map[string]any{"type": "script", "unix_path": "scripts/tool"},
			"system-tool": map[string]any{"type": "system", "command": "tool"},
		},
	}
}

func v8SchemaExamples() []schemaExample {
	withCommandField := func(command, field string, value any) map[string]any {
		manifest := validV8SkillManifest()
		manifest["commands"].(map[string]any)[command].(map[string]any)[field] = value
		return manifest
	}
	withRequirement := func(command string, value any) map[string]any {
		manifest := validV8SkillManifest()
		manifest["commands"].(map[string]any)[command].(map[string]any)["toolchain"] = value
		return manifest
	}
	dropToolchain := func(command string) map[string]any {
		manifest := validV8SkillManifest()
		delete(manifest["commands"].(map[string]any)[command].(map[string]any), "toolchain")
		return manifest
	}
	exactManifest := withRequirement("build-tool", requirement("go", exactly("1.23.4")))
	kotlinManifest := withRequirement("build-tool", requirement("kotlin", atLeast("2.0.0")))

	examples := []schemaExample{
		{name: "valid-exact-requirement", valid: true, instance: exactManifest},
		// The schema admits the closed identifier set; equality with the driver's
		// registry primary is the manager's own check, reported as
		// build_toolchain_requirement_invalid with violation id_not_primary
		// (preflight case 21). The suite's valid flag folds both layers, so the
		// case is invalid here and the layer distinction is the vector's.
		{name: "invalid-identifier-not-the-drivers-primary", instance: kotlinManifest},
		{name: "invalid-local-command-without-toolchain", instance: dropToolchain("build-tool")},
		{name: "invalid-repository-command-without-toolchain", instance: dropToolchain("golden-tool")},
		{name: "invalid-toolchain-as-a-bare-string", instance: withRequirement("build-tool", "go1.23.4")},
		{name: "invalid-toolchain-without-version", instance: withRequirement("build-tool", map[string]any{"id": "go"})},
		{name: "invalid-toolchain-without-id", instance: withRequirement("build-tool", map[string]any{"version": atLeast(goBaselineVersion)})},
		{name: "invalid-unknown-toolchain-identifier", instance: withRequirement("build-tool", requirement("clang", atLeast("18.0.0")))},
		{name: "invalid-jdk-is-companion-only", instance: withRequirement("build-tool", requirement("jdk", atLeast("21.0.0")))},
		{name: "invalid-unknown-version-kind", instance: withRequirement("build-tool",
			map[string]any{"id": "go", "version": map[string]any{"kind": "at_most", "max": "1.25.0"}})},
		{name: "invalid-range-without-below", instance: withRequirement("build-tool",
			map[string]any{"id": "go", "version": map[string]any{"kind": "range", "min": goBaselineVersion}})},
		{name: "invalid-exact-with-an-extra-member", instance: withRequirement("build-tool",
			map[string]any{"id": "go", "version": map[string]any{"kind": "exact", "equals": "1.23.4", "min": "1.23.0"}})},
		{name: "invalid-version-literal-with-a-go-prefix", instance: withRequirement("build-tool", requirement("go", atLeast("go1.23.4")))},
		{name: "invalid-version-literal-with-a-v-prefix", instance: withRequirement("build-tool", requirement("go", atLeast("v1.23.4")))},
		{name: "invalid-version-literal-two-components", instance: withRequirement("build-tool", requirement("go", atLeast("1.23")))},
		{name: "invalid-version-literal-leading-zero", instance: withRequirement("build-tool", requirement("go", atLeast("1.023.0")))},
		{name: "invalid-version-literal-prerelease", instance: withRequirement("build-tool", requirement("go", atLeast("1.23.0-rc1")))},
		{name: "invalid-version-literal-wildcard", instance: withRequirement("build-tool", requirement("go", atLeast("1.23.*")))},
		{name: "invalid-version-literal-component-overflow", instance: withRequirement("build-tool", requirement("go", atLeast("1.1000000.0")))},
		{name: "invalid-version-literal-executable-path", instance: withRequirement("build-tool", requirement("go", atLeast("/usr/local/go")))},
		{name: "invalid-version-literal-url", instance: withRequirement("build-tool", requirement("go", atLeast("https://example.test/go.tgz")))},
		{name: "invalid-version-literal-track", instance: withRequirement("build-tool", requirement("go", atLeast("nightly")))},
		{name: "invalid-generic-driver", instance: withCommandField("build-tool", "driver", "go-v2")},
	}
	for _, forbidden := range forbiddenWireFieldNames {
		examples = append(examples, schemaExample{
			name:     "invalid-v8-command-" + forbidden.field,
			instance: withCommandField("build-tool", forbidden.field, forbidden.value),
		})
	}
	return examples
}

func validSkillBuildV2() map[string]any {
	return map[string]any{
		"schema_version": 2,
		"targets": map[string]any{
			"golden-tool": map[string]any{
				"driver": "go-repository-v1", "build_root": ".", "source_dir": "cmd/golden-tool",
				"toolchain": requirement("go", atLeast(goBaselineVersion)),
			},
			"admin-tool": map[string]any{
				"driver": "go-repository-v1", "build_root": "tools/admin", "source_dir": "tools/admin/cmd/admin",
			},
		},
	}
}

func skillBuildV2SchemaExamples() []schemaExample {
	withField := func(target, field string, value any) map[string]any {
		descriptor := validSkillBuildV2()
		descriptor["targets"].(map[string]any)[target].(map[string]any)[field] = value
		return descriptor
	}
	noRequirement := validSkillBuildV2()
	delete(noRequirement["targets"].(map[string]any)["golden-tool"].(map[string]any), "toolchain")

	examples := []schemaExample{
		{name: "valid-optional-toolchain-absent", valid: true, instance: noRequirement},
		{name: "valid-exact-toolchain", valid: true, instance: withField("admin-tool", "toolchain", requirement("go", exactly("1.23.4")))},
		{name: "invalid-source-outside-build-root", instance: withField("admin-tool", "source_dir", "cmd/tool")},
		{name: "invalid-toolchain-as-a-bare-string", instance: withField("golden-tool", "toolchain", "go1.23.4")},
		{name: "invalid-version-literal-prerelease", instance: withField("golden-tool", "toolchain", requirement("go", atLeast("1.23.0-rc1")))},
		{name: "invalid-schema-1-version", instance: map[string]any{"schema_version": 1, "targets": validSkillBuildV2()["targets"]}},
	}
	for _, forbidden := range forbiddenWireFieldNames {
		examples = append(examples, schemaExample{
			name:     "invalid-target-" + forbidden.field,
			instance: withField("golden-tool", forbidden.field, forbidden.value),
		})
	}
	return examples
}

func toolchainRegistrySchemaExamples() []schemaExample {
	mutate := func(change func(entry map[string]any)) map[string]any {
		document := toolchainRegistry()
		entries := document["entries"].([]any)
		change(entries[0].(map[string]any))
		return document
	}
	return []schemaExample{
		{name: "invalid-complete-entry-without-compatibility", instance: mutate(func(entry map[string]any) {
			delete(entry, "compatibility")
		})},
		{name: "invalid-complete-entry-without-platforms", instance: mutate(func(entry map[string]any) {
			delete(entry, "platforms")
		})},
		{name: "invalid-baseline-prerelease-literal", instance: mutate(func(entry map[string]any) {
			entry["baseline"] = atLeast("1.23.0-rc1")
		})},
		{name: "invalid-fingerprint-algorithm", instance: mutate(func(entry map[string]any) {
			entry["fingerprint_algorithm"] = "sha256"
		})},
		{name: "invalid-unanchored-normalization", instance: mutate(func(entry map[string]any) {
			entry["normalization"].(map[string]any)["anchored"] = false
		})},
		{name: "invalid-unbounded-probe-output", instance: mutate(func(entry map[string]any) {
			delete(entry["normalization"].(map[string]any), "max_output_bytes")
		})},
		{name: "invalid-download-url-on-an-entry", instance: mutate(func(entry map[string]any) {
			entry["download_url"] = "https://go.dev/dl/go1.23.4.tar.gz"
		})},
		{name: "invalid-install-command-on-an-entry", instance: mutate(func(entry map[string]any) {
			entry["install_command"] = "brew install go"
		})},
		{name: "invalid-classifier-with-one-class", instance: mutate(func(entry map[string]any) {
			source := entry["metadata_sources"].([]any)[0].(map[string]any)
			source["fields"].([]any)[0].(map[string]any)["classes"] = []any{
				catchAllClass("unclassifiable", "compared", "unclassifiable"),
			}
		})},
		{name: "invalid-unknown-class-outcome", instance: mutate(func(entry map[string]any) {
			source := entry["metadata_sources"].([]any)[0].(map[string]any)
			classes := source["fields"].([]any)[0].(map[string]any)["classes"].([]any)
			classes[1].(map[string]any)["outcome"] = "honor"
		})},
		{name: "invalid-unknown-operating-system-relpath", instance: mutate(func(entry map[string]any) {
			entry["primary_relpath"].(map[string]any)["freebsd"] = "bin/go"
		})},
	}
}

func guidanceCatalogSchemaExamples() []schemaExample {
	mutate := func(change func(document map[string]any, entries []any)) map[string]any {
		document := guidanceCatalog()
		change(document, document["entries"].([]any))
		return document
	}
	return []schemaExample{
		{name: "invalid-guidance-id-without-a-revision", instance: mutate(func(_ map[string]any, entries []any) {
			entries[0].(map[string]any)["guidance_id"] = "toolchain.go.changed.any"
		})},
		{name: "invalid-guidance-id-revision-leading-zero", instance: mutate(func(_ map[string]any, entries []any) {
			entries[0].(map[string]any)["guidance_id"] = "toolchain.go.changed.any.r01"
		})},
		{name: "invalid-unknown-reason", instance: mutate(func(_ map[string]any, entries []any) {
			entries[0].(map[string]any)["reason"] = "install_failed"
		})},
		{name: "invalid-unknown-guidance-class", instance: mutate(func(_ map[string]any, entries []any) {
			entries[0].(map[string]any)["guidance_class"] = "vendor"
		})},
		{name: "invalid-non-https-primary-source", instance: mutate(func(_ map[string]any, entries []any) {
			entries[0].(map[string]any)["primary_source"] = "http://go.dev/doc/install"
		})},
		{name: "invalid-install-command-primary-source", instance: mutate(func(_ map[string]any, entries []any) {
			entries[0].(map[string]any)["primary_source"] = "brew install go"
		})},
		{name: "invalid-active-entry-with-superseded-by", instance: mutate(func(_ map[string]any, entries []any) {
			entries[0].(map[string]any)["superseded_by"] = guidanceID("go", "changed", "any", 2)
		})},
		{name: "invalid-entry-with-an-install-script", instance: mutate(func(_ map[string]any, entries []any) {
			entries[0].(map[string]any)["install_command"] = "brew install go"
		})},
		{name: "invalid-catalog-version-zero", instance: mutate(func(document map[string]any, _ []any) {
			document["catalog_version"] = 0
		})},
	}
}

func diagnosticSchemaExamples() []schemaExample {
	payloads := diagnosticPayloads()
	examples := make([]schemaExample, 0, len(payloads)+12)
	for index, payload := range payloads {
		name := "valid-site-" + itoa(index+1) + "-" + payload["code"].(string) + "-" + payload["stage"].(string)
		examples = append(examples, schemaExample{name: name, valid: true, instance: payload})
	}
	invalid := func(name string, change func(payload map[string]any), index int) schemaExample {
		payload := deepCloneMap(payloads[index])
		change(payload)
		return schemaExample{name: name, instance: payload}
	}
	examples = append(examples,
		invalid("invalid-requirement-invalid-carries-a-resolved-version", func(payload map[string]any) {
			payload["resolved_version"] = goResolvedVersion
		}, 0),
		invalid("invalid-requirement-invalid-carries-an-effective-requirement", func(payload map[string]any) {
			payload["effective_requirement"] = interval(goBaselineVersion, "", false)
		}, 0),
		invalid("invalid-requirement-invalid-echoes-the-offending-value", func(payload map[string]any) {
			payload["value"] = "/usr/local/go"
		}, 0),
		invalid("invalid-unknown-violation-token", func(payload map[string]any) {
			payload["violation"] = "smuggled_influence"
		}, 0),
		invalid("invalid-requirement-unsatisfiable-carries-an-effective-requirement", func(payload map[string]any) {
			payload["effective_requirement"] = interval(goBaselineVersion, "", false)
		}, 1),
		invalid("invalid-unavailable-carries-a-resolved-version", func(payload map[string]any) {
			payload["resolved_version"] = goResolvedVersion
			payload["prerelease"] = false
		}, 2),
		invalid("invalid-unavailable-without-an-effective-requirement", func(payload map[string]any) {
			delete(payload, "effective_requirement")
		}, 2),
		invalid("invalid-prerelease-unsupported-with-a-release-flag", func(payload map[string]any) {
			payload["prerelease"] = false
		}, 3),
		invalid("invalid-untested-release-without-admitted-families", func(payload map[string]any) {
			delete(payload, "admitted_families")
		}, 4),
		invalid("invalid-metadata-mismatch-with-a-free-text-assertion", func(payload map[string]any) {
			payload["assertion"] = "needs a newer toolchain"
		}, 5),
		invalid("invalid-untrusted-origin-without-an-origin-class", func(payload map[string]any) {
			delete(payload, "origin_class")
		}, 7),
		invalid("invalid-untrusted-shape-with-an-origin-class", func(payload map[string]any) {
			payload["origin_class"] = "ambient_path"
		}, 8),
		invalid("invalid-host-pair-check-with-a-reported-target", func(payload map[string]any) {
			payload["reported_target"] = "darwin/arm64"
		}, 10),
		invalid("invalid-native-target-check-with-supported-platforms", func(payload map[string]any) {
			payload["supported_platforms"] = goPlatforms()
		}, 11),
		invalid("invalid-guidance-id-without-a-revision", func(payload map[string]any) {
			payload["guidance_id"] = "toolchain.go.unavailable.macos"
		}, 2),
		invalid("invalid-diagnostic-carrying-prose-guidance", func(payload map[string]any) {
			payload["guidance"] = "run brew install go"
		}, 2),
		invalid("invalid-diagnostic-carrying-a-url", func(payload map[string]any) {
			payload["url"] = "https://go.dev/doc/install"
		}, 2),
	)
	return examples
}
