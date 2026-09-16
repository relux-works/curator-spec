package main

import "path/filepath"

// Umbrella provider trust-root vectors (environments §11, finding E4).
//
// Each case fixes a filesystem layout — the install directory, the
// machine-configuration provider_directories list, the ambient PATH
// entries, the manager-published and managed directories, and the files
// present — and states the required outcome under both rollout profiles:
// revision A (warning release, ambient-PATH selection kept, outside roots
// warns) and revision B (flip release, trust roots only, PATH-only refused,
// PATH search is a diagnostic-only probe).
//
// `present` entries carry an `executable` flag: a non-executable file of
// the provider name is skipped, never resolved. `unreadable_dirs` names
// trust roots that cannot be read: lookup fails with
// `subcommand_provider_root_unreadable`, never absence, never a fallback.
// Outcomes carry the details §11 requires: `migration_hint_directory`
// exactly when revision A warns, `untrusted_path` plus
// `trust_roots_consulted` on every `subcommand_provider_untrusted`
// refusal, `trust_roots_consulted` on every
// `subcommand_provider_missing` outcome, and `unreadable_directory` plus
// `trust_roots_consulted` on every unreadable failure.

func writeUmbrellaProviderResolutionVectors(dir string) {
	resolved := func(path string) map[string]any {
		return map[string]any{"resolved": path, "diagnostic": nil}
	}
	refusedUntrusted := func(untrustedPath string, roots []any) map[string]any {
		return map[string]any{
			"resolved": nil, "diagnostic": "subcommand_provider_untrusted",
			"untrusted_path": untrustedPath, "trust_roots_consulted": roots,
		}
	}
	warned := func(path, hintDirectory string, roots []any) map[string]any {
		return map[string]any{
			"resolved": path, "diagnostic": "subcommand_provider_outside_trust_roots",
			"migration_hint_directory": hintDirectory, "trust_roots_consulted": roots,
		}
	}
	missing := func(roots []any) map[string]any {
		return map[string]any{
			"resolved": nil, "diagnostic": "subcommand_provider_missing",
			"trust_roots_consulted": roots,
		}
	}
	unreadable := func(directory string, roots []any) map[string]any {
		return map[string]any{
			"resolved": nil, "diagnostic": "subcommand_provider_root_unreadable",
			"unreadable_directory": directory, "trust_roots_consulted": roots,
		}
	}
	present := func(path string, executable bool) map[string]any {
		return map[string]any{"path": path, "executable": executable}
	}
	base := func(name string) map[string]any {
		return map[string]any{
			"name": name, "subcommand": "run", "executable_name": "curator-run",
			"install_dir":          "/opt/curator/bin",
			"provider_directories": []any{},
			"path_entries":         []any{"/usr/local/bin", "/usr/bin", "/bin"},
			"published_dirs":       []any{"/home/operator/.curator/bin"},
			"managed_dirs":         []any{"/home/operator/.curator/environments"},
			"present":              []any{},
			"unreadable_dirs":      []any{},
		}
	}
	with := func(case_ map[string]any, key string, value any) map[string]any {
		case_[key] = value
		return case_
	}
	rootsOf := func(install string, listed ...string) []any {
		roots := []any{install}
		for _, entry := range listed {
			roots = append(roots, entry)
		}
		return roots
	}

	installOnly := base("install-dir-provider-missing-then-resolved")
	with(installOnly, "present", []any{present("/opt/curator/bin/curator-run", true)})
	installOnlyRoots := rootsOf("/opt/curator/bin")
	installOnly["revision_a"] = missing(installOnlyRoots)
	installOnly["revision_b"] = resolved("/opt/curator/bin/curator-run")

	installBeatsListed := base("install-dir-beats-listed-directory")
	with(installBeatsListed, "provider_directories", []any{"/opt/curator/providers"})
	with(installBeatsListed, "present", []any{
		present("/opt/curator/bin/curator-run", true),
		present("/opt/curator/providers/curator-run", true),
	})
	installBeatsListedRoots := rootsOf("/opt/curator/bin", "/opt/curator/providers")
	installBeatsListed["revision_a"] = missing(installBeatsListedRoots)
	installBeatsListed["revision_b"] = resolved("/opt/curator/bin/curator-run")

	listedDir := base("listed-directory-provider-resolved")
	with(listedDir, "provider_directories", []any{"/opt/curator/providers"})
	with(listedDir, "present", []any{
		present("/opt/curator/providers/curator-run", true),
		present("/usr/local/bin/curator-run", true),
	})
	listedDirRoots := rootsOf("/opt/curator/bin", "/opt/curator/providers")
	listedDir["revision_a"] = warned("/usr/local/bin/curator-run", "/usr/local/bin", listedDirRoots)
	listedDir["revision_b"] = resolved("/opt/curator/providers/curator-run")

	listedOrder := base("listed-order-first-match-wins")
	with(listedOrder, "provider_directories", []any{"/opt/curator/providers", "/srv/team/curator-providers"})
	with(listedOrder, "present", []any{
		present("/opt/curator/providers/curator-run", true),
		present("/srv/team/curator-providers/curator-run", true),
	})
	listedOrderRoots := rootsOf("/opt/curator/bin", "/opt/curator/providers", "/srv/team/curator-providers")
	listedOrder["revision_a"] = missing(listedOrderRoots)
	listedOrder["revision_b"] = resolved("/opt/curator/providers/curator-run")

	s6Planted := base("s6-planted-path-provider-warns-then-refuses")
	s6Planted["threat"] = "finding S6: a project .agents/env.sh sourced on directory change prepends /home/operator/work/acme/.bin to PATH, planting curator-run; finding E4 is that dispatch executing it"
	with(s6Planted, "path_entries", []any{"/home/operator/work/acme/.bin", "/usr/local/bin", "/usr/bin", "/bin"})
	with(s6Planted, "present", []any{present("/home/operator/work/acme/.bin/curator-run", true)})
	s6Roots := rootsOf("/opt/curator/bin")
	s6Planted["revision_a"] = warned("/home/operator/work/acme/.bin/curator-run", "/home/operator/work/acme/.bin", s6Roots)
	s6Planted["revision_b"] = refusedUntrusted("/home/operator/work/acme/.bin/curator-run", s6Roots)

	nonExecutable := base("non-executable-in-trust-root-skipped")
	with(nonExecutable, "provider_directories", []any{"/opt/curator/providers"})
	with(nonExecutable, "present", []any{
		present("/opt/curator/providers/curator-run", false),
		present("/usr/local/bin/curator-run", true),
	})
	nonExecutableRoots := rootsOf("/opt/curator/bin", "/opt/curator/providers")
	nonExecutable["revision_a"] = warned("/usr/local/bin/curator-run", "/usr/local/bin", nonExecutableRoots)
	nonExecutable["revision_b"] = refusedUntrusted("/usr/local/bin/curator-run", nonExecutableRoots)

	published := base("manager-published-directory-refused")
	with(published, "path_entries", []any{"/home/operator/.curator/bin", "/usr/bin", "/bin"})
	with(published, "present", []any{present("/home/operator/.curator/bin/curator-run", true)})
	publishedRoots := rootsOf("/opt/curator/bin")
	published["revision_a"] = refusedUntrusted("/home/operator/.curator/bin/curator-run", publishedRoots)
	published["revision_b"] = refusedUntrusted("/home/operator/.curator/bin/curator-run", publishedRoots)

	listedButPublished := base("listed-but-published-directory-still-refused")
	with(listedButPublished, "provider_directories", []any{"/home/operator/.curator/bin"})
	with(listedButPublished, "path_entries", []any{"/home/operator/.curator/bin", "/usr/bin", "/bin"})
	with(listedButPublished, "present", []any{present("/home/operator/.curator/bin/curator-run", true)})
	listedButPublishedRoots := rootsOf("/opt/curator/bin", "/home/operator/.curator/bin")
	listedButPublished["revision_a"] = refusedUntrusted("/home/operator/.curator/bin/curator-run", listedButPublishedRoots)
	listedButPublished["revision_b"] = refusedUntrusted("/home/operator/.curator/bin/curator-run", listedButPublishedRoots)

	managed := base("managed-directory-refused")
	with(managed, "path_entries", []any{"/home/operator/.curator/environments", "/usr/bin", "/bin"})
	with(managed, "present", []any{present("/home/operator/.curator/environments/curator-run", true)})
	managedRoots := rootsOf("/opt/curator/bin")
	managed["revision_a"] = refusedUntrusted("/home/operator/.curator/environments/curator-run", managedRoots)
	managed["revision_b"] = refusedUntrusted("/home/operator/.curator/environments/curator-run", managedRoots)

	unreadableListed := base("unreadable-listed-directory-fails")
	with(unreadableListed, "provider_directories", []any{"/opt/gone"})
	with(unreadableListed, "unreadable_dirs", []any{"/opt/gone"})
	with(unreadableListed, "present", []any{present("/usr/local/bin/curator-run", true)})
	unreadableListedRoots := rootsOf("/opt/curator/bin", "/opt/gone")
	unreadableListed["revision_a"] = unreadable("/opt/gone", unreadableListedRoots)
	unreadableListed["revision_b"] = unreadable("/opt/gone", unreadableListedRoots)

	unreadableInstall := base("unreadable-install-directory-fails")
	with(unreadableInstall, "unreadable_dirs", []any{"/opt/curator/bin"})
	with(unreadableInstall, "present", []any{present("/usr/local/bin/curator-run", true)})
	unreadableInstallRoots := rootsOf("/opt/curator/bin")
	unreadableInstall["revision_a"] = unreadable("/opt/curator/bin", unreadableInstallRoots)
	unreadableInstall["revision_b"] = unreadable("/opt/curator/bin", unreadableInstallRoots)

	pathWinsUnderA := base("path-selects-different-provider-while-trusted-exists")
	with(pathWinsUnderA, "present", []any{
		present("/opt/curator/bin/curator-run", true),
		present("/usr/local/bin/curator-run", true),
	})
	pathWinsUnderARoots := rootsOf("/opt/curator/bin")
	pathWinsUnderA["revision_a"] = warned("/usr/local/bin/curator-run", "/usr/local/bin", pathWinsUnderARoots)
	pathWinsUnderA["revision_b"] = resolved("/opt/curator/bin/curator-run")

	trustedOnPath := base("trusted-provider-on-path-resolves-silently")
	with(trustedOnPath, "provider_directories", []any{"/opt/curator/providers"})
	with(trustedOnPath, "path_entries", []any{"/opt/curator/providers", "/usr/bin", "/bin"})
	with(trustedOnPath, "present", []any{present("/opt/curator/providers/curator-run", true)})
	trustedOnPath["revision_a"] = resolved("/opt/curator/providers/curator-run")
	trustedOnPath["revision_b"] = resolved("/opt/curator/providers/curator-run")

	absent := base("provider-missing")
	absentRoots := rootsOf("/opt/curator/bin")
	absent["revision_a"] = missing(absentRoots)
	absent["revision_b"] = missing(absentRoots)

	writeJSON(filepath.Join(dir, "umbrella-provider-resolution.json"), map[string]any{
		"capability":          "agent-environments",
		"capability_revision": 1,
		"protocol_version":    protocolVersion,
		"schema_version":      1,
		"rule":                "umbrella provider trust roots (section 11)",
		"revision_a_profile":  "warning release: PATH selects, outside trust roots warns with subcommand_provider_outside_trust_roots",
		"revision_b_profile":  "flip release: trust roots only, PATH probe diagnostic, refused with subcommand_provider_untrusted",
		"cases": []any{
			installOnly, installBeatsListed, listedDir, listedOrder, s6Planted,
			nonExecutable, published, listedButPublished, managed,
			unreadableListed, unreadableInstall, pathWinsUnderA, trustedOnPath, absent,
		},
	})
}
