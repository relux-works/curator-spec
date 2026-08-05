package main

// Registry reachability, guidance-catalog coverage and lifecycle vectors:
// inventory cases 72 through 90, plus the registry halves 84a and 84b.

func registryOperatingSystems() []any {
	return []any{"linux", "macos", "windows"}
}

func gateCase(id, name, expected string, mutation map[string]any) map[string]any {
	value := map[string]any{"case": id, "name": name, "expected": map[string]any{"release_gate": expected}}
	if mutation != nil {
		value["mutation"] = mutation
	}
	return value
}

// toolchainRegistryCases apply the section 6.3 resolution and reachability
// properties to the registry itself. They are what makes the Stage A step 2
// host-pair check total: every host the manager reaches past step 2 has a
// relpath and a probe by construction.
func toolchainRegistryCases() []any {
	return []any{
		gateCase("84a", "registry-relpath-resolution", "fail", map[string]any{
			"entry":  "go",
			"remove": []any{"primary_relpath.windows"},
			"reason": "a complete entry missing a primary_relpath or a probe for an operating system in its platforms set is incomplete",
		}),
		gateCase("84b", "registry-relpath-reachability", "fail", map[string]any{
			"entry":  "go",
			"add":    []any{"probe.freebsd"},
			"reason": "a relpath or probe declared for an operating system outside the entry's platforms set is unreachable",
		}),
		gateCase("84a-probe", "registry-probe-resolution", "fail", map[string]any{
			"entry":  "go",
			"remove": []any{"probe.linux"},
			"reason": "resolution is checked over both per-operating-system tables",
		}),
		gateCase("84b-relpath", "registry-relpath-reachability-outside-platforms", "fail", map[string]any{
			"entry":  "go",
			"add":    []any{"primary_relpath.freebsd"},
			"reason": "reachability is checked over both per-operating-system tables",
		}),
		gateCase("registry-baseline", "shipped-registry-passes-the-gate", "pass", nil),
		gateCase("registry-reserved-entries-demand-nothing", "reserved-entries-demand-no-coverage", "pass", map[string]any{
			"reason": "a supported toolchain is one with a complete registry entry, so a reserved entry demands no guidance rows and no relpath",
		}),
	}
}

// guidanceReasonRows is the section 6.1 code-to-reason mapping, emitted so a
// conforming manager can assert the identity mapping rather than re-deriving it.
func guidanceReasonRows() []any {
	rows := make([]any, 0, len(toolchainReasons))
	for _, reason := range toolchainReasons {
		rows = append(rows, map[string]any{
			"code":           "build_toolchain_" + reason.code,
			"reason":         reason.code,
			"guidance_class": reason.class,
			"primary_source": guidanceOrigin(reason.class, reason.code),
		})
	}
	return rows
}

func guidanceCases() []any {
	var cases []any

	coverage := make([]any, 0, len(toolchainReasons)*3)
	for _, reason := range toolchainReasons {
		for _, operatingSystem := range registryOperatingSystems() {
			guidancePlatform := "any"
			revision := 1
			switch reason.code {
			case "unavailable":
				guidancePlatform = operatingSystem.(string)
			case "untrusted":
				if operatingSystem.(string) == "windows" {
					guidancePlatform = "windows"
					revision = 2
				}
			}
			coverage = append(coverage, map[string]any{
				"toolchain_id":      "go",
				"reason":            reason.code,
				"operating_system":  operatingSystem,
				"resolves_to":       guidanceID("go", reason.code, guidancePlatform, revision),
				"selected_platform": guidancePlatform,
				"active":            true,
			})
		}
	}
	cases = append(cases, map[string]any{
		"case": "72", "name": "every-reason-resolves-for-every-supported-toolchain-and-platform",
		"expected":   map[string]any{"release_gate": "pass"},
		"resolution": coverage,
	})

	cases = append(cases,
		gateCase("73", "missing-reason-for-a-supported-toolchain", "fail", map[string]any{
			"remove_tuple": map[string]any{"toolchain_id": "go", "reason": "changed"},
		}),
		gateCase("74", "two-active-entries-for-one-tuple", "fail", map[string]any{
			"add_active": map[string]any{
				"toolchain_id": "go", "reason": "changed", "platform": "any", "revision": 2,
			},
			"reason": "at most one entry per tuple is active",
		}),
		gateCase("75", "superseded-by-naming-a-lower-equal-or-absent-revision", "fail", map[string]any{
			"set_superseded_by": map[string]any{
				"guidance_id": guidanceID("go", "untrusted", "windows", 1),
				"values": []any{
					guidanceID("go", "untrusted", "windows", 1),
					guidanceID("go", "untrusted", "windows", 3),
				},
			},
			"reason": "superseded_by must name an existing entry of the same tuple at a strictly greater revision",
		}),
		gateCase("76", "superseded-by-naming-a-different-tuple", "fail", map[string]any{
			"set_superseded_by": map[string]any{
				"guidance_id": guidanceID("go", "untrusted", "windows", 1),
				"values":      []any{guidanceID("go", "unavailable", "windows", 2)},
			},
		}),
		map[string]any{
			"case": "77", "name": "a-superseded-entry-stays-resolvable",
			"expected": map[string]any{
				"release_gate":      "pass",
				"resolvable":        guidanceID("go", "untrusted", "windows", 1),
				"selection_returns": guidanceID("go", "untrusted", "windows", 2),
				"retained":          true,
			},
		},
	)

	emitted := make([]any, 0, len(toolchainReasons))
	for _, reason := range toolchainReasons {
		guidancePlatform, revision := "any", 1
		switch reason.code {
		case "unavailable":
			guidancePlatform = "macos"
		case "untrusted":
			guidancePlatform = "any"
		}
		emitted = append(emitted, map[string]any{
			"code":             "build_toolchain_" + reason.code,
			"operating_system": "macos",
			"guidance_id":      guidanceID("go", reason.code, guidancePlatform, revision),
			"revision":         revision,
			"active":           true,
		})
	}
	cases = append(cases, map[string]any{
		"case": "78", "name": "every-code-emits-an-active-revisioned-guidance-id",
		"expected":    map[string]any{"release_gate": "pass"},
		"diagnostics": emitted,
	})

	cases = append(cases,
		map[string]any{
			"case": "79", "name": "any-mode",
			"mode": "any",
			"expected": map[string]any{"release_gate": "pass",
				"shape": "one active any entry, no active exact entries"},
			"example_reason": "changed",
		},
		map[string]any{
			"case": "80", "name": "per-os-mode",
			"mode": "per_os",
			"expected": map[string]any{"release_gate": "pass",
				"shape": "one active exact entry for every registry operating system, no any entry"},
			"example_reason": "unavailable",
		},
		map[string]any{
			"case": "81", "name": "hybrid-coverage",
			"mode":           "hybrid",
			"example_reason": "untrusted",
			"expected": map[string]any{"release_gate": "pass",
				"resolution": []any{
					map[string]any{"operating_system": "linux", "resolves_to": guidanceID("go", "untrusted", "any", 1)},
					map[string]any{"operating_system": "macos", "resolves_to": guidanceID("go", "untrusted", "any", 1)},
					map[string]any{"operating_system": "windows", "resolves_to": guidanceID("go", "untrusted", "windows", 2)},
				}},
		},
		gateCase("82", "unreachable-fallback", "fail", map[string]any{
			"reason":        "an active any entry shadowed by active exact entries for every registry operating system can never be selected",
			"add_exact_for": []any{"linux", "macos"},
			"tuple":         map[string]any{"toolchain_id": "go", "reason": "untrusted"},
		}),
		gateCase("83", "unreachable-override", "fail", map[string]any{
			"reason":    "an active exact entry whose platform is outside the toolchain's registry platforms set is unreachable",
			"add_exact": map[string]any{"toolchain_id": "go", "reason": "changed", "platform": "linux"},
			"registry":  map[string]any{"entry": "go", "restrict_platforms_to": []any{"macos", "windows"}},
		}),
		gateCase("84", "operating-system-with-neither-exact-nor-any", "fail", map[string]any{
			"remove": []any{guidanceID("go", "unavailable", "linux", 1)},
			"reason": "every operating system in the registry platforms set must resolve to exactly one active entry",
		}),
	)
	return cases
}

// guidanceTransitionCases are the section 6.2.1 version transitions. A
// published catalog version is immutable in whole; every change is a transition
// from version N to N+1.
func guidanceTransitionCases() []any {
	tuple := map[string]any{"toolchain_id": "go", "reason": "untrusted", "platform": "windows"}
	return []any{
		map[string]any{
			"case": "85", "name": "retire-with-a-successor-across-versions",
			"transition": "retire_with_successor", "tuple": tuple,
			"from_revision": 1, "to_revision": 2,
			"expected": map[string]any{"release_gate": "pass"},
		},
		map[string]any{
			"case": "86", "name": "retire-without-a-successor-when-the-tuple-is-no-longer-required",
			"transition":   "retire_without_successor",
			"tuple":        map[string]any{"toolchain_id": "go", "reason": "unavailable", "platform": "linux"},
			"precondition": "the tuple's platform or toolchain left the registry",
			"expected":     map[string]any{"release_gate": "pass"},
		},
		map[string]any{
			"case": "87", "name": "an-entry-present-in-n-and-absent-from-n-plus-1",
			"transition": "remove", "expected": map[string]any{"release_gate": "fail"},
			"reason": "the entry set is append-only across versions",
		},
		map[string]any{
			"case": "88", "name": "a-carried-forward-entry-whose-immutable-members-differ",
			"transition": "carry_forward_modified",
			"members":    []any{"guidance_class", "primary_source", "summary"},
			"expected":   map[string]any{"release_gate": "fail"},
		},
		map[string]any{
			"case": "89", "name": "reactivating-a-retired-entry",
			"transition": "reactivate", "expected": map[string]any{"release_gate": "fail"},
			"reason": "active is one-way monotone, true to false and never back",
		},
		map[string]any{
			"case": "90", "name": "any-edit-inside-an-already-published-catalog-version",
			"transition": "edit_in_place", "expected": map[string]any{"release_gate": "fail"},
			"reason": "a published catalog version is immutable in whole, including active and superseded_by",
		},
	}
}
