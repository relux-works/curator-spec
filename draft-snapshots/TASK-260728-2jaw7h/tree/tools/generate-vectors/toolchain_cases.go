package main

// The section 8 vector inventory of
// docs/compiled-build-toolchain-requirements.md, case for case.
//
// Case identifiers are the inventory's own numbers, including its lettered
// sub-cases, so a reader can check coverage against the reference without a
// translation table. `tools/validate.py` asserts that the set of identifiers
// emitted here equals the inventory the contract requires.

func tcase(id, name string, fields map[string]any) map[string]any {
	value := map[string]any{"case": id, "name": name}
	for key, item := range fields {
		value[key] = item
	}
	return value
}

func fields(pairs ...any) map[string]any {
	value := map[string]any{}
	for index := 0; index+1 < len(pairs); index += 2 {
		value[pairs[index].(string)] = pairs[index+1]
	}
	return value
}

func permitted(extra map[string]any) map[string]any {
	value := map[string]any{"outcome": "permitted"}
	for key, item := range extra {
		value[key] = item
	}
	return value
}

func rejected(code, stage, step string, extra map[string]any) map[string]any {
	value := map[string]any{"outcome": "rejected", "code": code, "stage": stage, "step": step}
	for key, item := range extra {
		value[key] = item
	}
	return value
}

func declaration(channel, kind string) map[string]any {
	return map[string]any{"channel": channel, "kind": kind}
}

// noDeclaration is an empty channel map: neither `bundled` nor
// `operator_config` carries an entry for the identifier.
func noDeclaration() map[string]any {
	return map[string]any{"channel": nil, "kind": "absent"}
}

func goMod(directives map[string]any) map[string]any {
	return map[string]any{"go.mod": directives}
}

// beforeMutation is the assertion set every rejecting case carries: the
// operation failed before the manager committed anything.
func beforeMutation() map[string]any {
	return map[string]any{
		"acquisition_performed": false,
		"cache_lookup_reached":  false,
		"compiler_started":      false,
		"persistent_mutation":   false,
	}
}

// afterAcquisition is the Stage B assertion set: acquisition and audit already
// ran, and the failure still precedes cache lookup and every compiler child.
func afterAcquisition() map[string]any {
	return map[string]any{
		"acquisition_performed": true,
		"cache_lookup_reached":  false,
		"compiler_started":      false,
		"persistent_mutation":   false,
	}
}

// localStageB is the Stage B assertion set for a local command, whose source is
// a validated snapshot rather than an acquisition.
func localStageB() map[string]any {
	return map[string]any{
		"cache_lookup_reached": false,
		"compiler_started":     false,
		"persistent_mutation":  false,
	}
}

func preflightCases() []any {
	var cases []any
	cases = append(cases, positiveCases()...)
	cases = append(cases, requirementSurfaceCases()...)
	cases = append(cases, stageACases()...)
	cases = append(cases, stageBGoClassifierCases()...)
	cases = append(cases, stageBOtherMetadataCases()...)
	cases = append(cases, identityGuardCases()...)
	cases = append(cases, platformApplicabilityCases()...)
	cases = append(cases, declarationChannelCases()...)
	cases = append(cases, lateNarrowingCases()...)
	return cases
}

func positiveCases() []any {
	baseline := interval(goBaselineVersion, "", false)
	return []any{
		tcase("1", "schema-6-local-no-requirement", fields(
			"manifest_schema", 6, "driver", "go-v1",
			"expected", permitted(fields("effective_requirement", baseline,
				"requirement_source", "registry_baseline",
				"compatibility_family", []any{1, 23})))),
		tcase("2", "schema-7-external-no-requirement", fields(
			"manifest_schema", 7, "driver", "go-repository-v1", "descriptor_schema", 1,
			"expected", permitted(fields("effective_requirement", baseline,
				"requirement_source", "registry_baseline")))),
		tcase("3", "at-least-satisfied-at-the-bound", fields(
			"manifest_schema", 8, "requirement", requirement("go", atLeast("1.23.4")),
			"expected", permitted(fields("effective_requirement", interval("1.23.4", "", false))))),
		tcase("4", "range-satisfied-strictly-inside", fields(
			"manifest_schema", 8, "requirement", requirement("go", rangeOf("1.23.0", "1.25.0")),
			"expected", permitted(fields("effective_requirement", interval("1.23.0", "1.25.0", false))))),
		tcase("5", "exact-satisfied", fields(
			"manifest_schema", 8, "requirement", requirement("go", exactly("1.23.4")),
			"expected", permitted(fields("effective_requirement", interval("1.23.4", "1.23.4", true))))),
		tcase("6", "manifest-and-descriptor-intersect", fields(
			"manifest_schema", 8, "driver", "go-repository-v1", "descriptor_schema", 2,
			"requirement", requirement("go", atLeast("1.23.0")),
			"descriptor_requirement", requirement("go", rangeOf("1.23.0", "1.25.0")),
			"expected", permitted(fields("effective_requirement", interval("1.23.0", "1.25.0", false),
				"stage_a_effective_requirement", interval("1.23.0", "", false))))),
		tcase("7", "compatibility-preserve", fields(
			"manifest_schema", 8, "requirement", requirement("go", atLeast("1.23.0")),
			"resolved_version", "1.23.9",
			"expected", permitted(fields("effective_requirement", interval("1.23.0", "", false),
				"compatibility_family", []any{1, 23})))),
		tcase("8", "go-directive-release-below-resolved", fields(
			"manifest_schema", 6, "source_metadata", goMod(fields("go", "1.23.0")),
			"expected", permitted(fields("value_class", "release-literal", "assertion", atLeast("1.23.0"))))),
		tcase("9", "language-version-canonicalization", fields(
			"manifest_schema", 6, "resolved_version", "1.23.0",
			"source_metadata", goMod(fields("go", "1.23")),
			"expected", permitted(fields("value_class", "release-literal",
				"base_triple", []any{1, 23, 0}, "assertion", atLeast("1.23.0"),
				"note", "the canonical base triple and Go's own order agree whenever the comparand is a release")))),
		tcase("10", "go-directive-prerelease-at-or-below-resolved", fields(
			"manifest_schema", 6, "source_metadata", goMod(fields("go", "1.23rc1")),
			"expected", permitted(fields("value_class", "prerelease-literal", "base_triple", []any{1, 23, 0})))),
		tcase("11", "toolchain-release-name-at-or-below-resolved", fields(
			"manifest_schema", 6, "source_metadata", goMod(fields("go", "1.23.0", "toolchain", "go1.23.4")),
			"expected", permitted(fields("value_class", "release-name", "honored", false)))),
		tcase("12", "toolchain-default", fields(
			"manifest_schema", 6, "source_metadata", goMod(fields("go", "1.23.0", "toolchain", "default")),
			"expected", permitted(fields("value_class", "default", "honored", false)))),
		tcase("13", "toolchain-prerelease-name-at-or-below-resolved", fields(
			"manifest_schema", 6, "source_metadata", goMod(fields("go", "1.23.0", "toolchain", "go1.23rc1")),
			"expected", permitted(fields("value_class", "prerelease-name", "honored", false,
				"base_triple", []any{1, 23, 0})))),
		tcase("14", "no-toolchain-directive", fields(
			"manifest_schema", 6, "source_metadata", goMod(fields("go", "1.23.0")),
			"expected", permitted(fields("value_class", "absent", "assertion", nil)))),
		tcase("15", "rust-channel-stable", fields(
			"toolchain_id", "rust", "entry_status", "reserved", "resolved_version", "1.82.0",
			"source_metadata", map[string]any{"rust-toolchain.toml": fields("toolchain.channel", "stable")},
			"expected", permitted(fields("value_class", "release-track", "honored", false)))),
		tcase("16", "rust-channel-version-literal-at-or-below-resolved", fields(
			"toolchain_id", "rust", "entry_status", "reserved", "resolved_version", "1.82.0",
			"source_metadata", map[string]any{"rust-toolchain.toml": fields("toolchain.channel", "1.82.0")},
			"expected", permitted(fields("value_class", "version-literal", "honored", false)))),
		tcase("17", "one-probe-per-toolchain-per-operation", fields(
			"manifest_schema", 8, "commands", 2,
			"requirement", requirement("go", atLeast("1.23.0")),
			"expected", permitted(fields("probe_count", 1,
				"note", "Stage A runs once per operation per distinct toolchain, memoized only in operation-private state")))),
		tcase("18", "cache-hit-only-after-both-stages", fields(
			"manifest_schema", 8, "requirement", requirement("go", atLeast("1.23.0")),
			"cache", fields("candidate_toolchain_identity", "current", "expect_hit", true),
			"expected", permitted(fields("stage_a_passed", true, "stage_b_passed", true,
				"cache_lookup_reached", true, "cache_hit", true, "compiler_started", false)))),
		tcase("19", "cache-miss-by-toolchain-identity", fields(
			"manifest_schema", 8, "requirement", requirement("go", atLeast("1.23.0")),
			"cache", fields("candidate_toolchain_identity", "other", "expect_hit", false),
			"expected", permitted(fields("stage_a_passed", true, "stage_b_passed", true,
				"cache_lookup_reached", true, "cache_hit", false, "rebuilt", true,
				"rebuild_toolchain_identity", "current")))),
	}
}

func requirementSurfaceCases() []any {
	invalid := func(id, name string, violation string, requirementValue any, extra map[string]any) map[string]any {
		expected := fields("violation", violation,
			"source_ref", sourceRef("manifest", "/commands/build-tool/toolchain"),
			"effective_requirement_present", false, "resolved_version_present", false)
		for key, item := range extra {
			expected[key] = item
		}
		return tcase(id, name, fields(
			"manifest_schema", 8, "requirement", requirementValue,
			"expected", rejected("build_toolchain_requirement_invalid", "validation", "validation",
				merge(expected, beforeMutation()))))
	}
	return []any{
		invalid("20", "malformed-requirement-object", "not_an_object",
			map[string]any{"id": "go", "version": "1.23.0"}, nil),
		invalid("21", "identifier-not-the-drivers-primary", "id_not_primary",
			requirement("rust", atLeast("1.23.0")),
			fields("note", "the schema admits the closed identifier set; equality with the driver's registry primary is the manager's check")),
		invalid("22", "prerelease-literal-in-a-requirement", "version_literal_prerelease",
			map[string]any{"id": "go", "version": map[string]any{"kind": "at_least", "min": "1.23.0-rc1"}}, nil),
		invalid("23", "range-bounds-not-ordered", "range_bounds_not_ordered",
			requirement("go", rangeOf("1.25.0", "1.23.0")), nil),
		invalid("24", "version-literal-carrying-an-executable-path", "version_literal_malformed",
			map[string]any{"id": "go", "version": map[string]any{"kind": "at_least", "min": "/usr/local/go"}},
			fields("not_code", "build_toolchain_package_influence_forbidden",
				"note", "one input, one code: a malformed literal on the wire surface is never package influence",
				"value_echoed", false)),
		invalid("25", "version-literal-carrying-a-url", "version_literal_malformed",
			map[string]any{"id": "go", "version": map[string]any{"kind": "at_least", "min": "https://example.test/go.tgz"}},
			fields("not_code", "build_toolchain_package_influence_forbidden", "value_echoed", false)),
		invalid("26", "version-literal-carrying-a-track", "version_literal_malformed",
			map[string]any{"id": "go", "version": map[string]any{"kind": "at_least", "min": "nightly"}},
			fields("not_code", "build_toolchain_package_influence_forbidden", "value_echoed", false)),
		tcase("27", "manifest-command-added-toolchain-path-field", fields(
			"manifest_schema", 8, "suite", "schema-cases",
			"schema_case", "agent-skill-v8/invalid-v8-command-toolchain-path",
			"expected", rejected("manifest_invalid", "validation", "schema",
				merge(fields("toolchain_code_emitted", false,
					"note", "a key outside the closed field set is the existing schema rejection and never a build_toolchain_* code"),
					beforeMutation())))),
		tcase("28", "descriptor-target-added-toolchain-path-field", fields(
			"descriptor_schema", 2, "suite", "schema-cases",
			"schema_case", "skill-build-v2/invalid-target-toolchain-path",
			"expected", rejected("build_descriptor_invalid", "validation", "schema",
				merge(fields("toolchain_code_emitted", false), beforeMutation())))),
		tcase("29", "empty-intersection", fields(
			"manifest_schema", 8, "requirement", requirement("go", rangeOf("1.20.0", "1.22.0")),
			"expected", rejected("build_toolchain_requirement_unsatisfiable", "validation", "validation",
				merge(fields(
					"fragments", []any{
						map[string]any{"source_ref": sourceRef("registry", "go"), "requirement": atLeast(goBaselineVersion)},
						map[string]any{"source_ref": sourceRef("manifest", "/commands/build-tool/toolchain"), "requirement": rangeOf("1.20.0", "1.22.0")},
					},
					"conflict", fields(
						"lower_bound", goBaselineVersion,
						"lower_sources", []any{"registry_baseline"},
						"upper_bound", "1.22.0",
						"upper_sources", []any{sourceRef("manifest", "/commands/build-tool/toolchain")},
						"upper_inclusive", false),
					"effective_requirement_present", false,
					"resolved_version_present", false,
					"host_probed", false,
					"note", "an empty intersection is decided without probing the host, so it fails identically on every machine"),
					beforeMutation()))),
		),
	}
}

func merge(base map[string]any, extra map[string]any) map[string]any {
	value := map[string]any{}
	for key, item := range base {
		value[key] = item
	}
	for key, item := range extra {
		value[key] = item
	}
	return value
}

func stageACases() []any {
	baseline := interval(goBaselineVersion, "", false)
	stageA := func(id, name, code, step string, caseFields map[string]any, expectedExtra map[string]any) map[string]any {
		expected := merge(fields("effective_requirement", baseline), expectedExtra)
		return tcase(id, name, merge(fields("manifest_schema", 6,
			"expected", rejected(code, "A", step, merge(expected, beforeMutation()))), caseFields))
	}
	return []any{
		stageA("30", "declared-in-neither-channel", "build_toolchain_unavailable", "3a",
			fields("declaration", noDeclaration()),
			fields("note", "sub-step 3a is the only producer of this code and it produces no other")),
		stageA("31", "operator-config-entry-defers-to-path", "build_toolchain_untrusted", "3b",
			fields("declaration", declaration("operator_config", "path_lookup")),
			fields("substep", "origin", "origin_class", "ambient_path", "filesystem_read", false)),
		stageA("32", "operator-config-entry-names-a-version-manager-shim", "build_toolchain_untrusted", "3b",
			fields("declaration", declaration("operator_config", "version_manager_shim")),
			fields("substep", "origin", "origin_class", "version_manager_shim", "filesystem_read", false)),
		stageA("33", "declared-root-absent-on-disk", "build_toolchain_untrusted", "3c",
			fields("declaration", merge(declaration("operator_config", "concrete_root"), fields("root_exists", false))),
			fields("substep", "shape", "origin_class_present", false,
				"not_code", "build_toolchain_unavailable",
				"note", "a declared-but-broken root is untrusted, including when the root directory does not exist at all")),
		stageA("34", "declared-primary-absent", "build_toolchain_untrusted", "3c",
			fields("declaration", merge(declaration("operator_config", "concrete_root"), fields("primary_exists", false))),
			fields("substep", "shape", "origin_class_present", false, "not_code", "build_toolchain_unavailable")),
		stageA("35", "primary-outside-the-fingerprinted-tree", "build_toolchain_untrusted", "3c",
			fields("declaration", merge(declaration("operator_config", "concrete_root"), fields("primary_inside_tree", false))),
			fields("substep", "shape", "origin_class_present", false)),
		stageA("36", "unparseable-probe-output", "build_toolchain_version_undetermined", "4",
			fields("probe_output", "go version"),
			fields("probe", "version", "reason", "unmatched")),
		stageA("37", "devel-go-version", "build_toolchain_version_undetermined", "4",
			fields("probe_output", "go version devel go1.26-abcdef darwin/arm64"),
			fields("probe", "version", "reason", "unmatched",
				"note", "a devel or otherwise unprefixed field 2 is undetermined, never a default")),
		stageA("38", "prerelease-host", "build_toolchain_prerelease_unsupported", "5",
			fields("probe_output", "go version go1.24rc1 darwin/arm64", "resolved_version", "1.24.0", "prerelease", true),
			fields("resolved_version", "1.24.0", "prerelease", true)),
		stageA("39", "unsupported-host-pair", "build_toolchain_platform_unsupported", "2",
			fields("host_platform", platform("linux", "riscv64")),
			fields("check", "host_pair", "host_platform", platform("linux", "riscv64"),
				"supported_platforms", goPlatforms(), "resolved_version_present", false)),
		stageA("40", "reported-target-differs-from-native-target", "build_toolchain_platform_unsupported", "6",
			fields("reported_target", "linux/amd64"),
			fields("check", "native_target", "host_platform", platform("macos", "arm64"),
				"reported_target", "linux/amd64", "native_target", "darwin/arm64",
				"resolved_version", goResolvedVersion, "supported_platforms_present", false)),
		stageA("41", "resolved-below-min", "build_toolchain_incompatible", "7",
			fields("manifest_schema", 8, "requirement", requirement("go", atLeast("1.23.4")), "resolved_version", "1.23.0"),
			fields("effective_requirement", interval("1.23.4", "", false), "resolved_version", "1.23.0")),
		stageA("42", "resolved-at-the-exclusive-upper-bound", "build_toolchain_incompatible", "7",
			fields("manifest_schema", 8, "requirement", requirement("go", rangeOf("1.23.0", "1.23.4"))),
			fields("effective_requirement", interval("1.23.0", "1.23.4", false), "resolved_version", goResolvedVersion)),
		stageA("43", "compatibility-reject", "build_toolchain_untested_release", "8",
			fields("manifest_schema", 8, "requirement", requirement("go", atLeast("1.23.0")), "resolved_version", "1.99.0"),
			fields("resolved_version", "1.99.0", "admitted_families", []any{[]any{1, 23}},
				"note", "at_least alone admits nothing: the compatibility set is a separate, manager-owned gate")),
		stageA("44", "gate-precedence-incompatible-before-untested", "build_toolchain_incompatible", "7",
			fields("resolved_version", "1.22.0"),
			fields("resolved_version", "1.22.0", "not_code", "build_toolchain_untested_release",
				"note", "step 7 precedes step 8, although both gates would reject this host")),
	}
}

func stageBGoClassifierCases() []any {
	baseline := interval(goBaselineVersion, "", false)
	stageB := func(id, name, code, step string, metadata map[string]any, expectedExtra map[string]any) map[string]any {
		expected := merge(fields(
			"effective_requirement", baseline,
			"resolved_version", goResolvedVersion,
			"prerelease", false,
			"source_ref", sourceRef("source_metadata", "go.mod"),
		), expectedExtra)
		return tcase(id, name, fields(
			"manifest_schema", 6, "source_metadata", metadata,
			"expected", rejected(code, "B", step, merge(expected, localStageB()))))
	}
	mismatch := func(id, name string, metadata map[string]any, extra map[string]any) map[string]any {
		return stageB(id, name, "build_toolchain_metadata_mismatch", "5", metadata, extra)
	}
	forbidden := func(id, name string, metadata map[string]any, extra map[string]any) map[string]any {
		return stageB(id, name, "build_toolchain_package_influence_forbidden", "4", metadata, extra)
	}
	return []any{
		mismatch("45", "go-directive-release-above-resolved", goMod(fields("go", "1.24.0")),
			fields("value_class", "release-literal", "assertion", atLeast("1.24.0"),
				"source_ref", sourceRef("source_metadata", "go.mod#go"))),
		mismatch("46", "go-directive-unclassifiable-literal", goMod(fields("go", "v1.23")),
			fields("value_class", "unclassifiable", "assertion", "unclassifiable",
				"source_ref", sourceRef("source_metadata", "go.mod#go"))),
		mismatch("47", "go-directive-classifier-boundary-path-separator", goMod(fields("go", "1.23/4")),
			fields("value_class", "unclassifiable", "assertion", "unclassifiable",
				"source_ref", sourceRef("source_metadata", "go.mod#go"),
				"not_code", "build_toolchain_package_influence_forbidden",
				"note", "the go directive has no forbidden class, so a path separator is class 4 and not package influence")),
		mismatch("48", "toolchain-release-name-above-resolved", goMod(fields("go", "1.23.0", "toolchain", "go1.24.0")),
			fields("value_class", "release-name", "assertion", atLeast("1.24.0"),
				"source_ref", sourceRef("source_metadata", "go.mod#toolchain"))),
		mismatch("49", "toolchain-prerelease-name-above-resolved", goMod(fields("go", "1.23.0", "toolchain", "go1.24rc1")),
			fields("value_class", "prerelease-name", "assertion", atLeast("1.24.0"),
				"source_ref", sourceRef("source_metadata", "go.mod#toolchain"))),
		forbidden("50", "toolchain-custom-distribution-name", goMod(fields("go", "1.23.0", "toolchain", "go1.23.4-bigcorp")),
			fields("value_class", "custom-distribution-name",
				"source_ref", sourceRef("source_metadata", "go.mod#toolchain"),
				"note", "the suffix names where a toolchain comes from, which is the boundary forbidden is reserved for")),
		forbidden("51", "toolchain-path-bearing-name", goMod(fields("go", "1.23.0", "toolchain", "go1.23/../evil")),
			fields("value_class", "path-bearing-name",
				"source_ref", sourceRef("source_metadata", "go.mod#toolchain"))),
		mismatch("52", "toolchain-without-go-prefix", goMod(fields("go", "1.23.0", "toolchain", "1.23.4")),
			fields("value_class", "unclassifiable", "assertion", "unclassifiable",
				"source_ref", sourceRef("source_metadata", "go.mod#toolchain"))),
		stageB("53", "repeated-toolchain-directive", "build_toolchain_metadata_mismatch", "3",
			goMod(fields("go", "1.23.0", "toolchain", []any{"go1.23.4", "go1.23.4"})),
			fields("assertion", "unclassifiable", "value_class_present", false,
				"source_ref", sourceRef("source_metadata", "go.mod#toolchain"),
				"firing_site", "file_shape_gate",
				"note", "a repeated single-occurrence directive is a file-shape defect and yields no value to classify")),
		forbidden("54", "value-class-precedence-forbidden-before-compared", goMod(fields("go", "1.23.0", "toolchain", "go1.99.0-bigcorp")),
			fields("value_class", "custom-distribution-name",
				"source_ref", sourceRef("source_metadata", "go.mod#toolchain"),
				"note", "forbidden classes are matched first, although this value's version part would compare cleanly")),
	}
}

func stageBOtherMetadataCases() []any {
	rustResolved := "1.82.0"
	rustFile := func(pairs ...any) map[string]any {
		return map[string]any{"rust-toolchain.toml": fields(pairs...)}
	}
	rustCase := func(id, name, code, step string, metadata map[string]any, extra map[string]any) map[string]any {
		expected := merge(fields(
			"resolved_version", rustResolved, "prerelease", false,
			"source_ref", sourceRef("source_metadata", "rust-toolchain.toml"),
		), extra)
		return tcase(id, name, fields(
			"toolchain_id", "rust", "entry_status", "reserved",
			"resolved_version", rustResolved, "source_metadata", metadata,
			"expected", rejected(code, "B", step, merge(expected, localStageB()))))
	}
	return []any{
		rustCase("55", "rust-channel-nightly", "build_toolchain_metadata_mismatch", "5",
			rustFile("toolchain.channel", "nightly"),
			fields("value_class", "prerelease-track", "assertion", "unclassifiable",
				"source_ref", sourceRef("source_metadata", "rust-toolchain.toml#toolchain.channel"))),
		rustCase("56", "rust-channel-dated-nightly", "build_toolchain_metadata_mismatch", "5",
			rustFile("toolchain.channel", "nightly-2026-07-28"),
			fields("value_class", "prerelease-track", "assertion", "unclassifiable",
				"source_ref", sourceRef("source_metadata", "rust-toolchain.toml#toolchain.channel"))),
		rustCase("57", "rust-channel-beta", "build_toolchain_metadata_mismatch", "5",
			rustFile("toolchain.channel", "beta"),
			fields("value_class", "prerelease-track", "assertion", "unclassifiable",
				"source_ref", sourceRef("source_metadata", "rust-toolchain.toml#toolchain.channel"))),
		rustCase("58", "rust-channel-unclassifiable", "build_toolchain_metadata_mismatch", "5",
			rustFile("toolchain.channel", "bigcorp-2026"),
			fields("value_class", "unclassifiable", "assertion", "unclassifiable",
				"source_ref", sourceRef("source_metadata", "rust-toolchain.toml#toolchain.channel"))),
		rustCase("59", "rust-toolchain-path", "build_toolchain_package_influence_forbidden", "4",
			rustFile("toolchain.path", "/opt/nightly"),
			fields("value_class", "toolchain.path",
				"source_ref", sourceRef("source_metadata", "rust-toolchain.toml#toolchain.path"))),
		rustCase("60", "rust-disposition-precedence", "build_toolchain_package_influence_forbidden", "4",
			rustFile("toolchain.path", "/opt/nightly", "toolchain.channel", "nightly"),
			fields("value_class", "toolchain.path",
				"source_ref", sourceRef("source_metadata", "rust-toolchain.toml#toolchain.path"),
				"not_code", "build_toolchain_metadata_mismatch",
				"note", "every forbidden-disposition field is evaluated before every compared one")),
		tcase("61", "toolchain-tree-changed-between-stage-a-and-fingerprinting", fields(
			"manifest_schema", 6, "toolchain_mutation", "tree_changed_after_stage_a",
			"expected", rejected("build_toolchain_changed", "A", "fingerprint",
				merge(fields(
					"effective_requirement", interval(goBaselineVersion, "", false),
					"resolved_version", goResolvedVersion, "prerelease", false,
					"identity_before_present", true, "identity_after_present", true),
					beforeMutation())))),
		tcase("62", "external-command-fails-stage-a-with-no-acquisition", fields(
			"manifest_schema", 7, "driver", "go-repository-v1", "descriptor_schema", 1,
			"declaration", noDeclaration(),
			"expected", rejected("build_toolchain_unavailable", "A", "3a",
				merge(fields("effective_requirement", interval(goBaselineVersion, "", false),
					"note", "Stage A completes before external repository acquisition"),
					beforeMutation())))),
		tcase("63", "fail-fast-before-cache-lookup", fields(
			"manifest_schema", 8, "requirement", requirement("go", atLeast("1.23.4")),
			"resolved_version", "1.23.0",
			"cache", fields("candidate_toolchain_identity", "other", "expect_hit", false),
			"expected", rejected("build_toolchain_incompatible", "A", "7",
				merge(fields("effective_requirement", interval("1.23.4", "", false),
					"resolved_version", "1.23.0",
					"candidate_consulted", false, "rebuilt", false),
					beforeMutation())))),
		tcase("64", "dry-run-reports-blocked", fields(
			"manifest_schema", 6, "mode", "dry-run", "declaration", noDeclaration(),
			"expected", rejected("build_toolchain_unavailable", "A", "3a",
				merge(fields("effective_requirement", interval(goBaselineVersion, "", false),
					"report_state", "blocked", "not_report_state", "unsupported",
					"returns_failure", true,
					"note", "unsupported continues to mean an unknown driver and is never reused for a toolchain failure"),
					beforeMutation())))),
	}
}

func identityGuardCases() []any {
	return []any{
		tcase("91", "go-toolchain-identity-algorithm-unchanged", fields(
			"guard", "frozen_bytes", "subject", goToolchainFingerprint,
			"expected", permitted(fields("changed", false,
				"note", "adopting the requirement contract re-versions no fingerprint algorithm")))),
		tcase("92", "rc4-byte-frozen-digests-unchanged", fields(
			"guard", "frozen_bytes", "subject", "rc4-byte-frozen-digests",
			"expected", permitted(fields("changed", false)))),
		tcase("93", "requirement-change-alone-keeps-the-cache-key", fields(
			"guard", "cache_identity", "mutate", "manifest_requirement",
			"before", requirement("go", atLeast("1.23.0")), "after", requirement("go", atLeast("1.23.4")),
			"expected", permitted(fields("cache_key_changed", false,
				"note", "the effective requirement is a gate, not a build input")))),
		tcase("94", "compatibility-set-change-alone-keeps-the-cache-key", fields(
			"guard", "cache_identity", "mutate", "compatibility_set",
			"before", goCompatibility(),
			"after", map[string]any{"family_granularity": "major_minor", "families": []any{[]any{1, 23}, []any{1, 24}}},
			"expected", permitted(fields("cache_key_changed", false)))),
		tcase("95", "guidance-revision-change-alone-keeps-the-cache-key", fields(
			"guard", "cache_identity", "mutate", "guidance_catalog",
			"expected", permitted(fields("cache_key_changed", false,
				"note", "the catalog is not a cache, receipt, marker, or claim input")))),
	}
}

func platformApplicabilityCases() []any {
	baseline := interval(goBaselineVersion, "", false)
	unreached := fields(
		"declaration_channel_consulted", false,
		"primary_relpath_resolved", false,
		"probe_executed", false,
	)
	hostPair := func(id, name string, host map[string]any, caseExtra map[string]any, expectedExtra map[string]any) map[string]any {
		expected := merge(merge(fields(
			"effective_requirement", baseline,
			"check", "host_pair",
			"host_platform", host,
			"supported_platforms", goPlatforms(),
			"resolved_version_present", false,
		), unreached), expectedExtra)
		return tcase(id, name, merge(fields("manifest_schema", 6, "host_platform", host,
			"expected", rejected("build_toolchain_platform_unsupported", "A", "2",
				merge(expected, beforeMutation()))), caseExtra))
	}
	return []any{
		hostPair("96", "unsupported-operating-system", platform("freebsd", "amd64"), nil, nil),
		hostPair("97", "unsupported-architecture-on-a-supported-operating-system", platform("linux", "riscv64"), nil, nil),
		hostPair("98", "applicability-precedes-availability", platform("freebsd", "amd64"),
			fields("declaration", noDeclaration()),
			fields("not_code", "build_toolchain_unavailable",
				"note", "step 2 precedes sub-step 3a")),
		hostPair("99", "applicability-precedes-trust", platform("freebsd", "amd64"),
			fields("declaration", declaration("operator_config", "path_lookup")),
			fields("not_code", "build_toolchain_untrusted")),
		hostPair("100", "host-pair-payload", platform("freebsd", "amd64"), nil,
			fields("prerelease_present", false, "reported_target_present", false,
				"payload_members", []any{"check", "code", "driver", "effective_requirement",
					"guidance_id", "host_platform", "stage", "supported_platforms", "toolchain_id"})),
		tcase("101", "native-target-payload", fields(
			"manifest_schema", 6, "reported_target", "linux/amd64",
			"expected", rejected("build_toolchain_platform_unsupported", "A", "6",
				merge(fields(
					"effective_requirement", baseline,
					"check", "native_target",
					"host_platform", platform("macos", "arm64"),
					"reported_target", "linux/amd64",
					"native_target", "darwin/arm64",
					"resolved_version", goResolvedVersion,
					"prerelease", false,
					"supported_platforms_present", false,
					"payload_members", []any{"check", "code", "driver", "effective_requirement",
						"guidance_id", "host_platform", "native_target", "prerelease",
						"reported_target", "resolved_version", "stage", "toolchain_id"}),
					beforeMutation())))),
	}
}

func declarationChannelCases() []any {
	baseline := interval(goBaselineVersion, "", false)
	return []any{
		tcase("102", "installed-on-path-declared-nowhere", fields(
			"manifest_schema", 6, "declaration", noDeclaration(), "host_state", "toolchain_on_path",
			"expected", rejected("build_toolchain_unavailable", "A", "3a",
				merge(fields("effective_requirement", baseline,
					"not_code", "build_toolchain_untrusted",
					"origin_classification_performed", false,
					"note", "PATH is not a channel, so 3a finds nothing and 3b has nothing to classify"),
					beforeMutation())))),
		tcase("103", "declared-nowhere-absent-from-the-host", fields(
			"manifest_schema", 6, "declaration", noDeclaration(), "host_state", "toolchain_absent",
			"expected", rejected("build_toolchain_unavailable", "A", "3a",
				merge(fields("effective_requirement", baseline,
					"origin_classification_performed", false,
					"note", "the outcome does not depend on what is installed"),
					beforeMutation())))),
		tcase("104", "code-is-reported-per-identifier", fields(
			"manifest_schema", 6, "plan_toolchains", []any{"go", "rust"},
			"declarations", map[string]any{
				"go":   declaration("operator_config", "concrete_root"),
				"rust": noDeclaration(),
			},
			"expected", rejected("build_toolchain_unavailable", "A", "3a",
				merge(fields("toolchain_id", "rust", "resolved_toolchains", []any{"go"},
					"note", "Stage A runs for every distinct toolchain in the plan in lexical order, and failure of any fails the operation"),
					beforeMutation())))),
		tcase("105", "origin-classification-reads-only-the-entry", fields(
			"manifest_schema", 6,
			"declaration", merge(declaration("operator_config", "environment_reference"), fields("reference", "GOROOT")),
			"expected", rejected("build_toolchain_untrusted", "A", "3b",
				merge(fields("effective_requirement", baseline,
					"substep", "origin", "origin_class", "environment_variable",
					"filesystem_read", false),
					beforeMutation())))),
		tcase("106", "shape-classification-reads-only-the-filesystem", fields(
			"manifest_schema", 6,
			"declaration", merge(declaration("operator_config", "concrete_root"), fields("primary_on_disk", "shim_script")),
			"expected", rejected("build_toolchain_untrusted", "A", "3c",
				merge(fields("effective_requirement", baseline,
					"substep", "shape", "origin_class_present", false),
					beforeMutation())))),
	}
}

func lateNarrowingCases() []any {
	external := func(id, name string, manifestRequirement, descriptorRequirement map[string]any,
		resolved string, expected map[string]any) map[string]any {
		return tcase(id, name, fields(
			"manifest_schema", 8, "driver", "go-repository-v1", "descriptor_schema", 2,
			"requirement", manifestRequirement, "descriptor_requirement", descriptorRequirement,
			"resolved_version", resolved,
			"descriptor_readable_at_stage_a", false,
			"expected", expected))
	}
	return []any{
		external("107", "non-empty-late-intersection-excluding-the-resolved-host",
			requirement("go", atLeast("1.23.0")), requirement("go", atLeast("1.24.0")), "1.23.0",
			rejected("build_toolchain_incompatible", "B", "2",
				merge(fields(
					"stage_a_passed", true,
					"stage_a_effective_requirement", interval("1.23.0", "", false),
					"effective_requirement", interval("1.24.0", "", false),
					"resolved_version", "1.23.0", "prerelease", false),
					afterAcquisition()))),
		external("108", "empty-late-intersection",
			requirement("go", rangeOf("1.23.0", "1.25.0")), requirement("go", exactly("1.26.0")), goResolvedVersion,
			rejected("build_toolchain_requirement_unsatisfiable", "B", "1",
				merge(fields(
					"stage_a_passed", true,
					"fragments", []any{
						map[string]any{"source_ref": sourceRef("registry", "go"), "requirement": atLeast(goBaselineVersion)},
						map[string]any{"source_ref": sourceRef("manifest", "/commands/golden-tool/toolchain"), "requirement": rangeOf("1.23.0", "1.25.0")},
						map[string]any{"source_ref": sourceRef("descriptor", "/targets/golden-tool/toolchain"), "requirement": exactly("1.26.0")},
					},
					"conflict", fields(
						"lower_bound", "1.26.0",
						"lower_sources", []any{sourceRef("descriptor", "/targets/golden-tool/toolchain")},
						"upper_bound", "1.25.0",
						"upper_sources", []any{sourceRef("manifest", "/commands/golden-tool/toolchain")},
						"upper_inclusive", false),
					"effective_requirement_present", false,
					"resolved_version", goResolvedVersion, "prerelease", false,
					"byte_identical_under_reordered_sources", true),
					afterAcquisition()))),
		external("109", "late-narrowing-that-still-admits-the-host",
			requirement("go", atLeast("1.23.0")), requirement("go", atLeast("1.23.0")), goResolvedVersion,
			permitted(fields("stage_a_passed", true, "stage_b_step_1_passed", true, "stage_b_step_2_passed", true,
				"effective_requirement", interval("1.23.0", "", false)))),
		external("110", "stage-b-step-1-precedes-step-2",
			requirement("go", rangeOf("1.23.0", "1.23.4")), requirement("go", exactly("1.26.0")), goResolvedVersion,
			rejected("build_toolchain_requirement_unsatisfiable", "B", "1",
				merge(fields("not_code", "build_toolchain_incompatible",
					"resolved_version", goResolvedVersion, "prerelease", false,
					"effective_requirement_present", false,
					"note", "the host would also fail step 2, and step 1 fires first"),
					afterAcquisition()))),
		external("111", "requirement-gates-precede-metadata-work",
			requirement("go", atLeast("1.23.0")), requirement("go", atLeast("1.24.0")), "1.23.0",
			rejected("build_toolchain_incompatible", "B", "2",
				merge(fields(
					"effective_requirement", interval("1.24.0", "", false),
					"resolved_version", "1.23.0", "prerelease", false,
					"not_code", "build_toolchain_package_influence_forbidden",
					"forbidden_metadata_present", true,
					"note", "steps 1 and 2 precede the file-shape gate and every disposition"),
					afterAcquisition()))),
		external("112", "compatibility-is-not-re-evaluated-at-stage-b",
			requirement("go", atLeast("1.23.0")), requirement("go", atLeast("1.23.0")), goResolvedVersion,
			permitted(fields("stage_a_compatibility_verdict", "admitted",
				"stage_b_compatibility_evaluated", false,
				"untested_release_from_stage_b", false,
				"note", "the set is manager-owned and the resolved version did not change between the stages"))),
		tcase("113", "local-commands-are-unaffected-by-late-narrowing", fields(
			"manifest_schema", 8, "driver", "go-v1", "requirement", requirement("go", atLeast("1.23.0")),
			"descriptor_schema", nil,
			"expected", permitted(fields(
				"stage_a_effective_requirement", interval("1.23.0", "", false),
				"effective_requirement", interval("1.23.0", "", false),
				"stage_b_step_2_can_newly_fail", false)))),
	}
}
