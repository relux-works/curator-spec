package main

// Go version-literal grammar, classifier and boundary-probe vectors: inventory
// cases 114 through 127e.
//
// Go accepts a directive value through two independent layers. Curator pins
// both, because either alone admits values the Go command cannot use: the shape
// layer accepts `1.23.4rc1`, which the semantic layer cannot represent, and the
// semantic layer accepts a bare major `1`, which the shape layer rejects in the
// `go` directive.

const (
	goModVersionShape    = `^([1-9][0-9]*)\.(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))?([a-z]+[0-9]+)?$`
	goToolchainNameShape = `^default$|^go1($|\.)`
	goSemanticVersion    = `^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)|[a-z]+((0|[1-9][0-9]*))?)?)?$`
)

func goGrammars() map[string]any {
	return map[string]any{
		"goModVersionShape": map[string]any{
			"layer": "shape", "position": "go", "pattern": goModVersionShape,
			"upstream": "golang.org/x/mod/modfile GoVersionRE",
		},
		"goToolchainNameShape": map[string]any{
			"layer": "shape", "position": "toolchain", "pattern": goToolchainNameShape,
			"upstream": "golang.org/x/mod/modfile ToolchainRE",
		},
		"goSemanticVersion": map[string]any{
			"layer": "semantic", "position": "both", "pattern": goSemanticVersion,
			"upstream": "internal/gover.Parse, with cmd/go/internal/gover.FromToolchain for a name",
		},
		"admitted": map[string]any{
			"go":        "goModVersionShape AND goSemanticVersion",
			"toolchain": "goToolchainNameShape AND (default OR version part in goSemanticVersion)",
		},
	}
}

func classRow(index int, name, match, disposition, outcome string) map[string]any {
	return map[string]any{
		"class": index, "name": name, "match": match,
		"disposition": disposition, "outcome": outcome,
	}
}

func goDirectiveClasses() []any {
	return []any{
		classRow(1, "absent", "the directive is not present", "ignored", "no_assertion"),
		classRow(2, "release-literal",
			"goModVersionShape AND goSemanticVersion, with no prerelease group",
			"compared", "compare_base_triple"),
		classRow(3, "prerelease-literal",
			"goModVersionShape AND goSemanticVersion, with a prerelease group",
			"compared", "compare_base_triple"),
		classRow(4, "unclassifiable", "anything else", "compared", "unclassifiable"),
	}
}

func toolchainDirectiveClasses() []any {
	return []any{
		classRow(1, "absent", "the directive is not present", "ignored", "no_assertion"),
		classRow(2, "path-bearing-name", `the value contains / or \`, "forbidden", "package_influence_forbidden"),
		classRow(3, "custom-distribution-name",
			"goToolchainNameShape and a non-empty suffix after -, space or tab",
			"forbidden", "package_influence_forbidden"),
		classRow(4, "default", "the value is exactly default", "compared", "permitted_not_honored"),
		classRow(5, "release-name",
			"goToolchainNameShape and a version part in goSemanticVersion with no prerelease group",
			"compared", "compare_base_triple"),
		classRow(6, "prerelease-name",
			"goToolchainNameShape and a version part in goSemanticVersion with a prerelease group",
			"compared", "compare_base_triple"),
		classRow(7, "unclassifiable", "anything else", "compared", "unclassifiable"),
	}
}

// alignmentRow records one value's verdict in both layers, the conjunction the
// Go command reaches, and this contract's classification of it.
//
// probeMeasured says whether the section 4.2.1.2 boundary probe carries the
// value in its own table. The distinction is the point of the fixture: the
// upstream column of a measured row is corroborated against a real toolchain,
// and the upstream column of an unmeasured row is authored. Marking it keeps a
// reader from taking an authored claim for an observed one, and
// `tools/validate.py` holds every measured row to the probe's own class and
// disposition, so a fixture that drifts from the probe is caught without any
// particular Go toolchain being installed on the runner.
func alignmentRow(position, value string, shape, semantic, upstream bool, class int, disposition, outcome string, probeMeasured bool) map[string]any {
	return map[string]any{
		"position": position, "value": value,
		"shape_layer": shape, "semantic_layer": semantic, "upstream_admitted": upstream,
		"class": class, "disposition": disposition, "outcome": outcome,
		"probe_measured": probeMeasured,
	}
}

// goAlignmentTable carries both layers' verdicts per value, so a case that
// matches only the shape layer fails property P1. The upstream column here is
// authored; the section 4.2.1.2 boundary probe supplies the observed one.
func goAlignmentTable() map[string]any {
	rows := []any{
		alignmentRow("go", "1.23", true, true, true, 2, "compared", "compare_base_triple", true),
		alignmentRow("go", "1.23.4", true, true, true, 2, "compared", "compare_base_triple", true),
		alignmentRow("go", "1.21.0", true, true, true, 2, "compared", "compare_base_triple", true),
		alignmentRow("go", "1.23.0", true, true, true, 2, "compared", "compare_base_triple", false),
		alignmentRow("go", "1.24.0", true, true, true, 2, "compared", "compare_base_triple", false),
		alignmentRow("go", "1.26.0", true, true, true, 2, "compared", "compare_base_triple", true),
		alignmentRow("go", "1.99.0", true, true, true, 2, "compared", "compare_base_triple", true),
		alignmentRow("go", "1.23rc1", true, true, true, 3, "compared", "compare_base_triple", true),
		alignmentRow("go", "1.99rc1", true, true, true, 3, "compared", "compare_base_triple", true),
		alignmentRow("go", "1.23.4rc1", true, false, false, 4, "compared", "unclassifiable", true),
		alignmentRow("go", "1.24.0alpha1", true, false, false, 4, "compared", "unclassifiable", true),
		alignmentRow("go", "1.21.3beta2", true, false, false, 4, "compared", "unclassifiable", true),
		alignmentRow("go", "1", false, true, false, 4, "compared", "unclassifiable", true),
		alignmentRow("go", "0.1", false, true, false, 4, "compared", "unclassifiable", true),
		alignmentRow("go", "1.023", false, false, false, 4, "compared", "unclassifiable", true),
		alignmentRow("go", "1.23rc", false, true, false, 4, "compared", "unclassifiable", true),
		alignmentRow("go", "v1.23", false, false, false, 4, "compared", "unclassifiable", true),
		alignmentRow("go", "1.23/4", false, false, false, 4, "compared", "unclassifiable", true),
		alignmentRow("toolchain", "default", true, true, true, 4, "compared", "permitted_not_honored", true),
		alignmentRow("toolchain", "go1", true, true, true, 5, "compared", "compare_base_triple", true),
		alignmentRow("toolchain", "go1.99.0", true, true, true, 5, "compared", "compare_base_triple", true),
		alignmentRow("toolchain", "go1.23.4", true, true, true, 5, "compared", "compare_base_triple", false),
		alignmentRow("toolchain", "go1.24.0", true, true, true, 5, "compared", "compare_base_triple", false),
		alignmentRow("toolchain", "go1.99rc1", true, true, true, 6, "compared", "compare_base_triple", true),
		alignmentRow("toolchain", "go1.23rc1", true, true, true, 6, "compared", "compare_base_triple", false),
		alignmentRow("toolchain", "go1.24rc1", true, true, true, 6, "compared", "compare_base_triple", false),
		alignmentRow("toolchain", "go1.", true, false, false, 7, "compared", "unclassifiable", true),
		alignmentRow("toolchain", "go1.99.0rc1x", true, false, false, 7, "compared", "unclassifiable", true),
		alignmentRow("toolchain", "go2.0.0", false, true, false, 7, "compared", "unclassifiable", true),
		alignmentRow("toolchain", "go1x", false, true, false, 7, "compared", "unclassifiable", true),
		alignmentRow("toolchain", "godefault", false, false, false, 7, "compared", "unclassifiable", true),
		alignmentRow("toolchain", "1.23.4", false, true, false, 7, "compared", "unclassifiable", true),
		alignmentRow("toolchain", "go1.99.0-custom", true, true, true, 3, "forbidden", "package_influence_forbidden", true),
		alignmentRow("toolchain", "go1.99.0-bigcorp", true, true, true, 3, "forbidden", "package_influence_forbidden", true),
		alignmentRow("toolchain", "go1.23.4-bigcorp", true, true, true, 3, "forbidden", "package_influence_forbidden", false),
		alignmentRow("toolchain", "go1.23/../evil", true, false, false, 2, "forbidden", "package_influence_forbidden", true),
	}
	return map[string]any{
		"rows": rows,
		"properties": []any{
			map[string]any{
				"case": "126", "name": "p1-no-widening", "statement": "C(p) is a subset of Upstream(p)",
				"expected": "hold",
				"note":     "every value the suite classifies as a permitted comparison is one the Go command admits in that position under the conjunction of both layers",
			},
			map[string]any{
				"case": "126a", "name": "p2-no-narrowing-outside-the-security-partition",
				"statement": "Upstream(p) minus F(p) is a subset of C(p)", "expected": "hold",
				"excluded": []any{"go1.99.0-custom", "go1.99.0-bigcorp", "go1.23.4-bigcorp", "go1.23/../evil"},
			},
			map[string]any{
				"case": "126b", "name": "the-security-partition-genuinely-subtracts",
				"value": "go1.99.0-custom", "position": "toolchain",
				"upstream_admitted": true, "code": "build_toolchain_package_influence_forbidden",
				"expected": "hold",
				"note":     "this is what makes C = Upstream unsatisfiable and P1 and P2 separate properties",
			},
			map[string]any{
				"case": "126c", "name": "the-security-partition-is-not-bounded-by-upstream-either",
				"value": "go1.23/../evil", "position": "toolchain",
				"upstream_admitted": false, "code": "build_toolchain_package_influence_forbidden",
				"expected": "hold",
				"note":     "F is neither a subset of nor disjoint from the upstream-admitted set; only C is pinned",
			},
			map[string]any{
				"case": "126d", "name": "empty-forbidden-partition-for-the-go-directive",
				"position": "go", "forbidden_values": []any{}, "expected": "hold",
				"note": "P2 collapses to C = Upstream at this position, and case 47's path-separator value is covered by class 4",
			},
		},
	}
}

// boundaryProbeContract is the executable check obligation of section 4.2.1.2.
// The probe is landed at tools/toolchain-boundary-probe and is required to be
// run against at least one real Go toolchain of each family in the manager's
// compatibility set.
func boundaryProbeContract() map[string]any {
	return map[string]any{
		"check":    "tools/toolchain-boundary-probe",
		"required": true,
		"cases": []any{
			map[string]any{
				"case": "127", "name": "boundary-probe",
				"requirement": "measure the shape and semantic layers independently per value and fail on any disagreement with the classifier tables or any violation of P1 or P2",
				"toolchains":  "at least one real Go toolchain of each family in the manager's compatibility set",
				"authority":   "a fixture table that disagrees with a probe run is a defect in the fixture, not in the probe",
			},
			map[string]any{
				"case": "127a", "name": "semantic-measurement-is-isolated-from-the-host-version",
				"requirement":  "carry at least one value inside both layers and above the runner's own release, measure it representable, and record the real command outcome as too-new rather than as a rejection",
				"disqualifier": "a step-2 verdict that is a bare exit status",
			},
			map[string]any{
				"case": "127b", "name": "isolated-and-command-measurements-agree",
				"requirement": "for every value the shape layer accepts and whose command outcome is recognised, compare the isolated verdict against the classified command outcome and fail on any disagreement",
			},
			map[string]any{
				"case": "127c", "name": "the-command-classifier-is-closed",
				"requirement":  "every command outcome falls inside the recognised set, and an outcome outside it fails the probe instead of being mapped to a verdict",
				"disqualifier": "a fall-through branch that names a verdict",
			},
			map[string]any{
				"case": "127d", "name": "regression-controls",
				"requirement": "the five superseded classifications, command forms and recognition families are runnable from the probe binary and each fails for its named reason, covering both laundering directions",
				"controls": []any{
					"open-classifier", "unrelated-command-failure", "tidy-exit",
					"patch-prerelease-compared", "c-equals-upstream",
				},
				"note": "a control that passes means the property it guards is no longer being tested",
			},
			map[string]any{
				"case": "127e", "name": "recognition-is-exact-and-its-closure-is-measured",
				"requirement":  "every recognised form is one whole diagnostic line predicted before the command ran, and a closure section classifies outcomes outside the recognised set and requires each to yield no verdict, in both laundering directions, reported separately",
				"disqualifier": "recognising a lead plus an unconstrained tail, or a substring anywhere in the output",
			},
		},
		"recognised_outcomes": map[string]any{
			"toolchain": []any{
				map[string]any{"form": "exit 0", "state": "accepted"},
				map[string]any{"form": `go: cannot find "V" in PATH`, "state": "accepted"},
				map[string]any{"form": `go: invalid toolchain "V" in go.mod`, "state": "rejected"},
				map[string]any{"form": `go: invalid GOTOOLCHAIN "V"`, "state": "rejected"},
			},
			"go": []any{
				map[string]any{"form": "exit 0", "state": "accepted"},
				map[string]any{"form": "go: go.mod requires go >= V (running go L; GOTOOLCHAIN=local)", "state": "too-new"},
				map[string]any{"form": "go.mod:3: invalid go version 'V': must match format 1.23.0", "state": "rejected"},
				map[string]any{"form": "panic: go: internal error: missing go root module", "state": "rejected"},
			},
			"anything_else": "unknown, which fails the probe",
		},
	}
}

func goMetadataCases() []any {
	resolved := goResolvedVersion
	stageBSite := func(step string) map[string]any {
		return map[string]any{
			"stage": "B", "step": step,
			"before_cache_lookup":   true,
			"before_compiler_child": true,
		}
	}
	shapeGate := func(id, name string, metadata map[string]any, extra map[string]any) map[string]any {
		expected := merge(fields(
			"outcome", "rejected",
			"code", "build_toolchain_metadata_mismatch",
			"assertion", "unclassifiable",
			"firing_site", "file_shape_gate",
			"value_class_present", false,
			"site", stageBSite("3"),
		), extra)
		return tcase(id, name, fields("resolved_version", resolved, "source_metadata", metadata, "expected", expected))
	}
	classified := func(id, name, position, value string, class int, className, outcome string, extra map[string]any) map[string]any {
		expected := merge(fields(
			"outcome", outcome,
			"position", position, "class", class, "value_class", className,
			"site", stageBSite("5"),
		), extra)
		metadata := goMod(fields("go", value))
		if position == "toolchain" {
			metadata = goMod(fields("go", "1.23.0", "toolchain", value))
		}
		return tcase(id, name, fields("resolved_version", resolved, "value", value,
			"source_metadata", metadata, "expected", expected))
	}
	mismatch := func(id, name, position, value string, class int, className string, extra map[string]any) map[string]any {
		return classified(id, name, position, value, class, className, "rejected",
			merge(fields("code", "build_toolchain_metadata_mismatch"), extra))
	}
	return []any{
		shapeGate("114", "repeated-go-directive", goMod(fields("go", []any{"1.23.0", "1.23.0"})),
			fields("source_ref", sourceRef("source_metadata", "go.mod#go"))),
		shapeGate("115", "repeated-toolchain-directive", goMod(fields("go", "1.23.0", "toolchain", []any{"go1.23.4", "go1.23.4"})),
			fields("source_ref", sourceRef("source_metadata", "go.mod#toolchain"),
				"matches_case", "53")),
		shapeGate("116", "unparseable-go-mod", map[string]any{"go.mod": "module"},
			fields("source_ref", sourceRef("source_metadata", "go.mod"))),
		shapeGate("117", "shape-gate-precedes-disposition-evaluation",
			map[string]any{"go.mod": "module", "rust-toolchain.toml": fields("toolchain.path", "/opt/nightly")},
			fields("source_ref", sourceRef("source_metadata", "go.mod"),
				"not_code", "build_toolchain_package_influence_forbidden",
				"note", "a field that cannot be extracted cannot be classified")),
		mismatch("118", "go-1-no-minor-component", "go", "1", 4, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", false, "semantic_layer", true,
				"note", "the shape-narrower-than-semantic half of the boundary")),
		mismatch("119", "go-zero-major", "go", "0.1", 4, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", false, "semantic_layer", true)),
		mismatch("120", "go-1-023-leading-zero", "go", "1.023", 4, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", false, "semantic_layer", false)),
		mismatch("121", "go-1-23rc-prerelease-letters-with-no-number", "go", "1.23rc", 4, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", false, "semantic_layer", true)),
		mismatch("122", "go-1-23-4rc1-patch-prerelease", "go", "1.23.4rc1", 4, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", true, "semantic_layer", false,
				"not_outcome", "permitted",
				"note", "matches goModVersionShape and so parses, but is outside goSemanticVersion; never a class-3 comparison against the resolved version")),
		mismatch("122a", "go-1-24-0alpha1-patch-prerelease", "go", "1.24.0alpha1", 4, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", true, "semantic_layer", false)),
		mismatch("122b", "go-1-21-3beta2-patch-prerelease", "go", "1.21.3beta2", 4, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", true, "semantic_layer", false)),
		tcase("122c", "layer-attribution", fields(
			"resolved_version", resolved,
			"expected", fields(
				"same_code", "build_toolchain_metadata_mismatch",
				"same_assertion", "unclassifiable",
				"different_firing_sites", []any{
					map[string]any{"case": "115", "input": "a repeated go or toolchain directive", "site": stageBSite("3"), "firing_site": "file_shape_gate"},
					map[string]any{"case": "122", "input": "go 1.23.4rc1", "site": stageBSite("5"), "firing_site": "value_classifier"},
				},
				"note", "the patch-prerelease value's file parses and its field extracts, so it is a classifier case"))),
		classified("122d", "go-1-23rc1-stays-permitted", "go", "1.23rc1", 3, "prerelease-literal", "permitted",
			fields("base_triple", []any{1, 23, 0}, "shape_layer", true, "semantic_layer", true,
				"note", "a prerelease after a minor with no patch is inside both layers, so case 122 narrows only the patch-prerelease region")),
		mismatch("122e", "future-release-is-a-comparison-not-a-grammar-failure", "go", "1.99.0", 2, "release-literal",
			fields("assertion", atLeast("1.99.0"), "not_assertion", "unclassifiable",
				"shape_layer", true, "semantic_layer", true,
				"note", "a representable value above the host fails on the comparison and never on the grammar")),
		mismatch("122f", "future-prerelease-same-route", "go", "1.99rc1", 3, "prerelease-literal",
			fields("assertion", atLeast("1.99.0"), "not_assertion", "unclassifiable",
				"shape_layer", true, "semantic_layer", true)),
		tcase("122g", "a-future-release-below-the-host-is-permitted", fields(
			"resolved_version", "1.26.1", "value", "1.26.0",
			"source_metadata", goMod(fields("go", "1.26.0")),
			"expected", fields("outcome", "permitted", "position", "go", "class", 2,
				"value_class", "release-literal", "base_triple", []any{1, 26, 0},
				"note", "case 122e turns on the comparison, not on the value being newer than any particular runner"))),
		classified("123", "toolchain-go1", "toolchain", "go1", 5, "release-name", "permitted",
			fields("base_triple", []any{1, 0, 0}, "honored", false, "not_class", 7,
				"note", "upstream reads go1 as 1.0.0")),
		mismatch("124", "toolchain-go1-trailing-dot", "toolchain", "go1.", 7, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", true, "semantic_layer", false)),
		mismatch("124a", "toolchain-go1-99-0rc1x", "toolchain", "go1.99.0rc1x", 7, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", true, "semantic_layer", false)),
		mismatch("125", "toolchain-go2-0-0", "toolchain", "go2.0.0", 7, "unclassifiable",
			fields("assertion", "unclassifiable", "shape_layer", false, "semantic_layer", true)),
	}
}
