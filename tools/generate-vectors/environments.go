package main

// The agent-environments revision-1 conformance surfaces of
// protocol/environments.md: the generation-header grammar, the section 5
// part-joining and chapter rules, zero-module and no-context outputs, the
// referenced-form layout, the managed opencode.json CCJ-1 bytes, the
// system-prompt output, and the section 5.6 surface hashes.

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

const (
	environmentHeaderMarker     = "curator-root-context-v1"
	environmentGeneratedLine    = "generated: Curator Protocol environments revision 1 (https://github.com/relux-works/curator-spec)"
	environmentNoticeLine       = "notice: generated file; direct edits are unsupported and are detected as drift; update the source profile repository or its composed profiles instead"
	environmentModulesDirectory = ".agent-context/modules"
	environmentSystemPromptPath = ".agent-context/system-prompt.md"

	precedenceLaterOverridesEarlier = "later-overrides-earlier"
	precedenceEarlierOverridesLater = "earlier-overrides-later"
)

// environmentRootTargets maps each revision-1 adapter to its home-relative
// root-context target from environments.md section 7.1.
var environmentRootTargets = map[string]string{
	"claude_code": "CLAUDE.md",
	"codex_cli":   "AGENTS.md",
	"opencode":    "AGENTS.md",
	"pi":          "AGENTS.md",
}

type environmentModule struct {
	path         string
	content      string
	class        string   // "" selects the default class root
	environments []string // nil selects every environment
}

type environmentProfile struct {
	name       string
	pin        string // exact header pin: "commit <hex>" or "state sha256:<hex>"
	hasContext bool
	modules    []environmentModule
}

func environmentFixtureProfiles() map[string]environmentProfile {
	return map[string]environmentProfile{
		"companyA": {
			name: "companyA", pin: "commit " + fixedCommit, hasContext: true,
			modules: []environmentModule{
				{path: "00-base.md", content: "# Base\n\nShared engineering context.\n"},
				{path: "10-style.md", content: "# Style\n\nWrite tersely.\n"},
				{path: "20-claude.md", content: "# Claude\n\nClaude-only guidance.\n", environments: []string{"claude_code"}},
				{path: "90-system.md", content: "You are the companyA reviewer.\n", class: "system"},
			},
		},
		"personal": {
			name: "personal", pin: "commit fedcba9876543210fedcba9876543210fedcba98", hasContext: true,
			modules: []environmentModule{
				{path: "00-base.md", content: "# Personal\n\nPersonal overlay context.\n"},
				{path: "90-system.md", content: "Prefer short answers.\n", class: "system"},
			},
		},
		"emptyoverlay": {
			name: "emptyoverlay", pin: "commit " + strings.Repeat("1", 40), hasContext: true,
		},
		"emptytoo": {
			name: "emptytoo", pin: "commit " + strings.Repeat("2", 40), hasContext: true,
		},
		"selective": {
			name: "selective", pin: "commit " + strings.Repeat("3", 40), hasContext: true,
			modules: []environmentModule{
				{path: "90-system.md", content: "Claude-only system prompt.\n", class: "system", environments: []string{"claude_code"}},
			},
		},
		"nocontext": {
			name: "nocontext", pin: "commit " + strings.Repeat("4", 40), hasContext: false,
		},
		"default": {
			name: "default", pin: "state sha256:" + strings.Repeat("ab", 32), hasContext: true,
			modules: []environmentModule{
				{path: "00-base.md", content: "# Default\n\nMigrated machine scope.\n"},
			},
		},
	}
}

// environmentHeader renders the section 5.1 generation header part.
func environmentHeader(chain []environmentProfile, precedence string) string {
	lines := []string{"<!--", environmentHeaderMarker, "profile: " + chain[0].name + " " + chain[0].pin}
	if len(chain) > 1 {
		for _, overlay := range chain[1:] {
			lines = append(lines, "compose: "+overlay.name+" "+overlay.pin)
		}
		lines = append(lines, "precedence: "+precedence)
	}
	lines = append(lines, environmentGeneratedLine, environmentNoticeLine, "-->")
	return strings.Join(lines, "\n") + "\n"
}

// environmentApplicable filters a profile's modules of one class for one
// environment under section 3: an absent selector applies everywhere.
func environmentApplicable(profile environmentProfile, environment, class string) []environmentModule {
	var applicable []environmentModule
	for _, module := range profile.modules {
		moduleClass := module.class
		if moduleClass == "" {
			moduleClass = "root"
		}
		if moduleClass != class {
			continue
		}
		if module.environments != nil {
			selected := false
			for _, identifier := range module.environments {
				if identifier == environment {
					selected = true
				}
			}
			if !selected {
				continue
			}
		}
		applicable = append(applicable, module)
	}
	return applicable
}

// environmentJoin joins parts under the section 5 rule: every part ends with
// exactly one LF and adjacent parts are separated by one additional LF.
func environmentJoin(parts []string) string {
	return strings.Join(parts, "\n")
}

func environmentChapter(profileName string) string {
	return "---\n\n## Profile: " + profileName + "\n"
}

func environmentReferencePath(profileName, modulePath string) string {
	return environmentModulesDirectory + "/" + profileName + "/" + modulePath
}

// environmentRootContextFiles materializes the root-context surface for a
// chain, environment, and form, returning the home-relative file set. A false
// first result means no root-context surface exists (section 2: the activated
// profile has no context directory).
func environmentRootContextFiles(chain []environmentProfile, environment, form, precedence string) (bool, map[string]string) {
	if !chain[0].hasContext {
		return false, nil
	}
	files := map[string]string{}
	parts := []string{environmentHeader(chain, precedence)}
	var instructions []string
	appendModule := func(profile environmentProfile, module environmentModule) {
		switch form {
		case "monolithic":
			parts = append(parts, module.content)
		case "referenced":
			reference := environmentReferencePath(profile.name, module.path)
			files[reference] = module.content
			instructions = append(instructions, reference)
			if environment != "opencode" {
				parts = append(parts, "@"+reference+"\n")
			}
		default:
			panic("unsupported root-context form " + form)
		}
	}
	if len(chain) == 1 {
		for _, module := range environmentApplicable(chain[0], environment, "root") {
			appendModule(chain[0], module)
		}
	} else {
		for _, profile := range chain {
			if environment != "opencode" || form != "referenced" {
				parts = append(parts, environmentChapter(profile.name))
			}
			for _, module := range environmentApplicable(profile, environment, "root") {
				appendModule(profile, module)
			}
		}
	}
	if environment == "opencode" && form == "referenced" {
		// Section 5.3: the opencode root file is the header part alone and
		// the managed opencode.json carries the ordered reference list as
		// CCJ-1 bytes followed by exactly one trailing LF.
		files[environmentRootTargets[environment]] = environmentHeader(chain, precedence)
		files["opencode.json"] = string(canonicalValue(map[string]any{"instructions": stringsToAny(instructions)})) + "\n"
		return true, files
	}
	files[environmentRootTargets[environment]] = environmentJoin(parts)
	return true, files
}

// environmentSystemPromptFiles materializes the section 5.5 system-prompt
// surface. A false first result means no applicable system module exists and
// the file is absent.
func environmentSystemPromptFiles(chain []environmentProfile, environment string) (bool, map[string]string) {
	var parts []string
	for _, profile := range chain {
		for _, module := range environmentApplicable(profile, environment, "system") {
			parts = append(parts, module.content)
		}
	}
	if len(parts) == 0 {
		return false, nil
	}
	return true, map[string]string{environmentSystemPromptPath: environmentJoin(parts)}
}

// environmentSurfaceHash computes the section 5.6 surface hash: the core
// section 8 content hash over the surface's home-relative file set.
func environmentSurfaceHash(files map[string]string) string {
	paths := make([]string, 0, len(files))
	for path := range files {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	digest := sha256.New()
	for index, path := range paths {
		if index > 0 {
			digest.Write([]byte{0})
		}
		digest.Write([]byte(path))
		digest.Write([]byte{0})
		digest.Write([]byte(files[path]))
	}
	return "sha256:" + hex.EncodeToString(digest.Sum(nil))
}

func environmentChainJSON(chain []environmentProfile) []any {
	members := make([]any, 0, len(chain))
	for _, profile := range chain {
		member := map[string]any{
			"name":        profile.name,
			"pin":         profile.pin,
			"has_context": profile.hasContext,
		}
		if profile.hasContext {
			modules := make([]any, 0, len(profile.modules))
			for _, module := range profile.modules {
				entry := map[string]any{"path": module.path, "content": module.content}
				if module.class != "" {
					entry["class"] = module.class
				}
				if module.environments != nil {
					entry["environments"] = stringsToAny(module.environments)
				}
				modules = append(modules, entry)
			}
			member["modules"] = modules
		}
		members = append(members, member)
	}
	return members
}

func environmentHeaderCase(name string, chain []environmentProfile, precedence any) map[string]any {
	direction := ""
	if text, ok := precedence.(string); ok {
		direction = text
	}
	header := environmentHeader(chain, direction)
	sum := sha256.Sum256([]byte(header))
	members := make([]any, 0, len(chain))
	for _, profile := range chain {
		members = append(members, map[string]any{"name": profile.name, "pin": profile.pin})
	}
	return map[string]any{
		"name":           name,
		"chain":          members,
		"precedence":     precedence,
		"expected_bytes": header,
		"sha256":         "sha256:" + hex.EncodeToString(sum[:]),
		"line_count":     strings.Count(header, "\n"),
	}
}

// writeEnvironmentVectors emits conformance/v1/vectors/environments.json and
// the byte-exact expected files below conformance/v1/expected/environments.
func writeEnvironmentVectors(dir, expected string) {
	profiles := environmentFixtureProfiles()
	chain := func(names ...string) []environmentProfile {
		members := make([]environmentProfile, 0, len(names))
		for _, name := range names {
			profile, ok := profiles[name]
			if !ok {
				panic("unknown environment fixture profile " + name)
			}
			members = append(members, profile)
		}
		return members
	}

	headerCases := []any{
		environmentHeaderCase("single-profile", chain("companyA"), nil),
		environmentHeaderCase("composed-default-precedence", chain("companyA", "personal", "emptyoverlay"), precedenceLaterOverridesEarlier),
		environmentHeaderCase("composed-earlier-overrides-later", chain("companyA", "personal"), precedenceEarlierOverridesLater),
		environmentHeaderCase("local-state-pin", chain("default"), nil),
	}

	type materializationInput struct {
		name        string
		surface     string
		environment string
		form        string
		chain       []environmentProfile
		precedence  any
	}
	inputs := []materializationInput{
		{"monolithic-claude-code", "root-context", "claude_code", "monolithic", chain("companyA"), nil},
		{"monolithic-codex-selector-excluded", "root-context", "codex_cli", "monolithic", chain("companyA"), nil},
		{"monolithic-composed-empty-chapter", "root-context", "claude_code", "monolithic", chain("companyA", "personal", "emptyoverlay"), precedenceLaterOverridesEarlier},
		{"monolithic-zero-modules", "root-context", "claude_code", "monolithic", chain("emptyoverlay"), nil},
		{"monolithic-zero-modules-composed", "root-context", "claude_code", "monolithic", chain("emptyoverlay", "emptytoo"), precedenceLaterOverridesEarlier},
		{"referenced-claude-code-composed", "root-context", "claude_code", "referenced", chain("companyA", "personal"), precedenceLaterOverridesEarlier},
		{"referenced-opencode", "root-context", "opencode", "referenced", chain("companyA"), nil},
		{"referenced-opencode-zero-modules", "root-context", "opencode", "referenced", chain("emptyoverlay"), nil},
		{"no-context-directory", "root-context", "claude_code", "monolithic", chain("nocontext"), nil},
		{"system-prompt-composed", "system-prompt", "claude_code", "", chain("companyA", "personal"), precedenceLaterOverridesEarlier},
		{"system-prompt-none-applicable", "system-prompt", "codex_cli", "", chain("selective"), nil},
	}

	materializationCases := make([]any, 0, len(inputs))
	for _, input := range inputs {
		direction := ""
		if text, ok := input.precedence.(string); ok {
			direction = text
		}
		var written bool
		var files map[string]string
		if input.surface == "system-prompt" {
			written, files = environmentSystemPromptFiles(input.chain, input.environment)
		} else {
			written, files = environmentRootContextFiles(input.chain, input.environment, input.form, direction)
		}
		item := map[string]any{
			"name":         input.name,
			"surface":      input.surface,
			"environment":  input.environment,
			"chain":        environmentChainJSON(input.chain),
			"precedence":   input.precedence,
			"file_written": written,
			"files":        []any{},
		}
		if input.surface == "root-context" {
			item["form"] = input.form
		}
		if written {
			paths := make([]string, 0, len(files))
			for path := range files {
				paths = append(paths, path)
			}
			sort.Strings(paths)
			entries := make([]any, 0, len(paths))
			for _, path := range paths {
				payload := []byte(files[path])
				sum := sha256.Sum256(payload)
				relative := "expected/environments/" + input.name + "/" + path
				writeBytes(filepath.Join(expected, input.name, filepath.FromSlash(path)), payload)
				entries = append(entries, map[string]any{
					"path":     path,
					"expected": relative,
					"sha256":   "sha256:" + hex.EncodeToString(sum[:]),
				})
			}
			item["files"] = entries
			item["surface_sha256"] = environmentSurfaceHash(files)
		}
		materializationCases = append(materializationCases, item)
	}

	writeJSON(filepath.Join(dir, "environments.json"), map[string]any{
		"schema_version":        1,
		"protocol_version":      protocolVersion,
		"capability":            "agent-environments",
		"capability_revision":   1,
		"part_rule":             "every part ends with exactly one LF; the document is the parts joined with exactly one additional LF between adjacent parts",
		"header_cases":          headerCases,
		"materialization_cases": materializationCases,
	})
}

// validEnvironmentMarkerV1 is the positive .agent-environment.json example: a
// managed home of a composed git profile.
func validEnvironmentMarkerV1() map[string]any {
	return map[string]any{
		"version": 1,
		"profile": map[string]any{
			"name":            "companyA",
			"source_kind":     "git",
			"source_identity": map[string]any{"kind": "network-git", "value": "github.com/example/profiles"},
			"ref":             map[string]any{"kind": "tag", "value": "v1.2.0"},
			"commit":          fixedCommit,
		},
		"composition": []any{
			map[string]any{"name": "personal", "commit": "fedcba9876543210fedcba9876543210fedcba98"},
		},
		"precedence": precedenceLaterOverridesEarlier,
		"mode":       "managed-home",
		"surfaces": map[string]any{
			"root-context": map[string]any{
				"paths":          []any{"CLAUDE.md"},
				"form":           "monolithic",
				"content_sha256": "sha256:" + strings.Repeat("0", 64),
			},
			"skills": map[string]any{
				"paths":          []any{},
				"content_sha256": "sha256:" + strings.Repeat("1", 64),
			},
		},
	}
}

func environmentMarkerSchemaExamples(valid map[string]any) []schemaExample {
	localProfile := cloneMap(valid)
	localProfile["profile"] = map[string]any{
		"name": "default", "source_kind": "local", "state_sha256": strings.Repeat("ab", 32),
	}
	delete(localProfile, "composition")
	delete(localProfile, "precedence")

	pathProfile := cloneMap(valid)
	pathProfile["profile"] = map[string]any{
		"name": "authoring", "source_kind": "path",
		"source_path": "/Users/operator/profiles", "state_sha256": strings.Repeat("cd", 32),
	}
	delete(pathProfile, "composition")
	delete(pathProfile, "precedence")

	importedPathProfile := cloneMap(pathProfile)
	importedPathProfile["profile"].(map[string]any)["name"] = "imported"
	importedPathProfile["profile"].(map[string]any)["imported_from_native"] = true

	pathWithCommit := cloneMap(pathProfile)
	pathWithCommit["profile"].(map[string]any)["commit"] = fixedCommit

	pathWithRef := cloneMap(pathProfile)
	pathWithRef["profile"].(map[string]any)["ref"] = map[string]any{"kind": "branch", "value": "main"}

	pathMissingSourcePath := cloneMap(pathProfile)
	delete(pathMissingSourcePath["profile"].(map[string]any), "source_path")

	pathImportedFalse := cloneMap(pathProfile)
	pathImportedFalse["profile"].(map[string]any)["imported_from_native"] = false

	gitWithSourcePath := cloneMap(valid)
	gitWithSourcePath["profile"].(map[string]any)["source_path"] = "/Users/operator/profiles"

	linked := cloneMap(valid)
	linked["mode"] = "linked"
	for _, entry := range linked["surfaces"].(map[string]any) {
		entry.(map[string]any)["copy_fallback"] = false
	}
	linked["surfaces"].(map[string]any)["root-context"].(map[string]any)["copy_fallback"] = true

	noComposition := cloneMap(valid)
	delete(noComposition, "composition")
	delete(noComposition, "precedence")

	seededParent := cloneMap(noComposition)
	seededParent["seed_links"] = []any{"git", "nvim"}

	gitWithStatePin := cloneMap(valid)
	gitWithStatePin["profile"].(map[string]any)["state_sha256"] = strings.Repeat("ab", 32)

	localWithRef := cloneMap(localProfile)
	localWithRef["profile"].(map[string]any)["ref"] = map[string]any{"kind": "branch", "value": "main"}

	compositionWithoutPrecedence := cloneMap(valid)
	delete(compositionWithoutPrecedence, "precedence")

	precedenceWithoutComposition := cloneMap(valid)
	delete(precedenceWithoutComposition, "composition")

	emptyComposition := cloneMap(valid)
	emptyComposition["composition"] = []any{}

	managedHomeCopyFallback := cloneMap(valid)
	managedHomeCopyFallback["surfaces"].(map[string]any)["root-context"].(map[string]any)["copy_fallback"] = false

	linkedMissingCopyFallback := cloneMap(valid)
	linkedMissingCopyFallback["mode"] = "linked"

	seededLinked := cloneMap(linked)
	seededLinked["seed_links"] = []any{"git"}

	unsortedSurfaces := cloneMap(noComposition)
	unsortedSurfaces["surfaces"] = orderedSurfaceObject(
		[]string{"skills", "root-context"},
		unsortedSurfaces["surfaces"].(map[string]any),
	)

	missingSurfacePaths := cloneMap(valid)
	delete(missingSurfacePaths["surfaces"].(map[string]any)["skills"].(map[string]any), "paths")

	unknownField := cloneMap(valid)
	unknownField["environment"] = "claude_code"

	invalidMode := cloneMap(valid)
	invalidMode["mode"] = "adopted"

	return []schemaExample{
		{name: "valid-local-profile", valid: true, instance: localProfile},
		{name: "valid-path-profile", valid: true, instance: pathProfile},
		{name: "valid-imported-path-profile", valid: true, instance: importedPathProfile},
		{name: "valid-linked-copy-fallback", valid: true, instance: linked},
		{name: "valid-no-composition", valid: true, instance: noComposition},
		{name: "valid-seeded-opencode-parent", valid: true, instance: seededParent},
		{name: "invalid-version", valid: false, instance: withField(valid, "version", 2)},
		{name: "invalid-unknown-field", valid: false, instance: unknownField},
		{name: "invalid-git-with-state-pin", valid: false, instance: gitWithStatePin},
		{name: "invalid-git-with-source-path", valid: false, instance: gitWithSourcePath},
		{name: "invalid-local-with-ref", valid: false, instance: localWithRef},
		{name: "invalid-path-with-commit", valid: false, instance: pathWithCommit},
		{name: "invalid-path-with-ref", valid: false, instance: pathWithRef},
		{name: "invalid-path-missing-source-path", valid: false, instance: pathMissingSourcePath},
		{name: "invalid-path-imported-from-native-false", valid: false, instance: pathImportedFalse},
		{name: "invalid-mode", valid: false, instance: invalidMode},
		{name: "invalid-composition-without-precedence", valid: false, instance: compositionWithoutPrecedence},
		{name: "invalid-precedence-without-composition", valid: false, instance: precedenceWithoutComposition},
		{name: "invalid-empty-composition", valid: false, instance: emptyComposition},
		{name: "invalid-managed-home-copy-fallback", valid: false, instance: managedHomeCopyFallback},
		{name: "invalid-linked-missing-copy-fallback", valid: false, instance: linkedMissingCopyFallback},
		{name: "invalid-seed-links-on-linked-home", valid: false, instance: seededLinked},
		{name: "invalid-surfaces-unsorted", valid: false, instance: unsortedSurfaces},
		{name: "invalid-missing-surface-paths", valid: false, instance: missingSurfacePaths},
	}
}

// validLaunchEnvFragmentV1 is the section 10.2 positive example.
func validLaunchEnvFragmentV1() map[string]any {
	return map[string]any{
		"fragment":    "launch-env-fragment-v1",
		"environment": "claude_code",
		"profile":     map[string]any{"name": "companyA", "commit": fixedCommit},
		"composition": []any{
			map[string]any{"name": "personal", "commit": "fedcba9876543210fedcba9876543210fedcba98"},
		},
		"precedence": precedenceLaterOverridesEarlier,
		"env":        map[string]any{"CLAUDE_CONFIG_DIR": "/manager/environments/companyA/claude_code"},
		"system_prompt": map[string]any{
			"path": "/manager/environments/companyA/claude_code/.agent-context/system-prompt.md",
			"channels": []any{
				map[string]any{"kind": "flag", "semantics": "append", "flag": "--append-system-prompt-file"},
				map[string]any{"kind": "flag", "semantics": "replace", "flag": "--system-prompt-file"},
			},
		},
	}
}

func launchEnvFragmentSchemaExamples(valid map[string]any) []schemaExample {
	localStatePin := cloneMap(valid)
	localStatePin["profile"] = map[string]any{"name": "default", "state_sha256": strings.Repeat("ab", 32)}
	delete(localStatePin, "composition")
	delete(localStatePin, "precedence")

	noComposition := cloneMap(valid)
	delete(noComposition, "composition")
	delete(noComposition, "precedence")

	configKeyChannel := cloneMap(noComposition)
	configKeyChannel["environment"] = "codex_cli"
	configKeyChannel["env"] = map[string]any{"CODEX_HOME": "/manager/environments/companyA/codex_cli"}
	configKeyChannel["system_prompt"] = map[string]any{
		"path": "/manager/environments/companyA/codex_cli/.agent-context/system-prompt.md",
		"channels": []any{
			map[string]any{"kind": "config-key", "semantics": "replace", "key": "model_instructions_file"},
		},
	}

	emptyChannels := cloneMap(noComposition)
	emptyChannels["environment"] = "opencode"
	emptyChannels["env"] = map[string]any{"XDG_CONFIG_HOME": "/manager/environments/companyA/opencode"}
	emptyChannels["system_prompt"] = map[string]any{
		"path":     "/manager/environments/companyA/opencode/opencode/.agent-context/system-prompt.md",
		"channels": []any{},
	}

	fileChannels := cloneMap(noComposition)
	fileChannels["environment"] = "pi"
	fileChannels["env"] = map[string]any{"PI_CODING_AGENT_DIR": "/manager/environments/companyA/pi"}
	fileChannels["system_prompt"] = map[string]any{
		"path": "/manager/environments/companyA/pi/.agent-context/system-prompt.md",
		"channels": []any{
			map[string]any{"kind": "flag", "semantics": "append", "flag": "--append-system-prompt-file"},
			map[string]any{"kind": "flag", "semantics": "replace", "flag": "--system-prompt-file"},
			map[string]any{"kind": "file", "semantics": "append", "filename": "APPEND_SYSTEM.md"},
			map[string]any{"kind": "file", "semantics": "replace", "filename": "SYSTEM.md"},
		},
	}

	bothPins := cloneMap(valid)
	bothPins["profile"] = map[string]any{
		"name": "companyA", "commit": fixedCommit, "state_sha256": strings.Repeat("ab", 32),
	}

	compositionWithoutPrecedence := cloneMap(valid)
	delete(compositionWithoutPrecedence, "precedence")

	precedenceWithoutComposition := cloneMap(valid)
	delete(precedenceWithoutComposition, "composition")

	unknownKind := cloneMap(valid)
	unknownKind["system_prompt"].(map[string]any)["channels"].([]any)[0].(map[string]any)["kind"] = "env-file"

	unknownSemantics := cloneMap(valid)
	unknownSemantics["system_prompt"].(map[string]any)["channels"].([]any)[0].(map[string]any)["semantics"] = "prepend"

	flagWithFilename := cloneMap(valid)
	flagChannel := flagWithFilename["system_prompt"].(map[string]any)["channels"].([]any)[0].(map[string]any)
	delete(flagChannel, "flag")
	flagChannel["filename"] = "APPEND_SYSTEM.md"

	unknownVariable := cloneMap(valid)
	unknownVariable["env"] = map[string]any{"claude_config_dir": "/manager/environments/companyA/claude_code"}

	emptyEnv := cloneMap(valid)
	emptyEnv["env"] = map[string]any{}

	return []schemaExample{
		{name: "valid-local-state-pin", valid: true, instance: localStatePin},
		{name: "valid-no-composition", valid: true, instance: noComposition},
		{name: "valid-config-key-channel", valid: true, instance: configKeyChannel},
		{name: "valid-empty-channels", valid: true, instance: emptyChannels},
		{name: "valid-file-channels", valid: true, instance: fileChannels},
		{name: "invalid-fragment-identity", valid: false, instance: withField(valid, "fragment", "launch-env-fragment-v2")},
		{name: "invalid-unknown-environment", valid: false, instance: withField(valid, "environment", "cursor")},
		{name: "invalid-unknown-field", valid: false, instance: withField(valid, "channel", "flag")},
		{name: "invalid-profile-both-pins", valid: false, instance: bothPins},
		{name: "invalid-composition-without-precedence", valid: false, instance: compositionWithoutPrecedence},
		{name: "invalid-precedence-without-composition", valid: false, instance: precedenceWithoutComposition},
		{name: "invalid-unknown-channel-kind", valid: false, instance: unknownKind},
		{name: "invalid-unknown-semantics", valid: false, instance: unknownSemantics},
		{name: "invalid-flag-channel-with-filename", valid: false, instance: flagWithFilename},
		{name: "invalid-lowercase-variable-name", valid: false, instance: unknownVariable},
		{name: "invalid-empty-env", valid: false, instance: emptyEnv},
	}
}

func profilefileSchemaExamples(valid map[string]any) []schemaExample {
	badName := cloneMap(valid)
	badName["profiles"] = map[string]any{"bad name": "profiles/bad"}

	traversal := cloneMap(valid)
	traversal["profiles"] = map[string]any{"companyA": "../outside"}

	duplicateDirectory := cloneMap(valid)
	duplicateDirectory["profiles"] = map[string]any{
		"companyA": "profiles/shared", "personal": "profiles/shared",
	}

	nestedRoot := cloneMap(valid)
	nestedRoot["profiles"] = map[string]any{
		"companyA": "profiles/companyA", "personal": "profiles/companyA/inner",
	}

	return []schemaExample{
		{name: "valid-single-profile", valid: true, instance: map[string]any{
			"version": 1, "profiles": map[string]any{"companyA": "profiles/companyA"},
		}},
		{name: "invalid-version", valid: false, instance: withField(valid, "version", 2)},
		{name: "invalid-unknown-field", valid: false, instance: withField(valid, "notes", "informative")},
		{name: "invalid-profile-name", valid: false, instance: badName},
		{name: "invalid-traversal-path", valid: false, instance: traversal},
		{name: "invalid-duplicate-directory", valid: false, instance: duplicateDirectory},
		{name: "invalid-nested-root", valid: false, instance: nestedRoot},
	}
}

func validContextManifestV1() map[string]any {
	return map[string]any{
		"version": 1,
		"modules": []any{
			map[string]any{"path": "00-base.md"},
			map[string]any{"path": "10-style.md"},
			map[string]any{"path": "20-claude.md", "environments": []any{"claude_code"}},
			map[string]any{"path": "90-system.md", "class": "system"},
		},
	}
}

func contextManifestSchemaExamples(valid map[string]any) []schemaExample {
	moduleEntry := func(entry map[string]any) map[string]any {
		manifest := cloneMap(valid)
		manifest["modules"] = []any{entry}
		return manifest
	}
	duplicatePath := cloneMap(valid)
	duplicatePath["modules"] = []any{
		map[string]any{"path": "00-base.md"},
		map[string]any{"path": "00-base.md", "class": "system"},
	}
	return []schemaExample{
		{name: "valid-empty-modules", valid: true, instance: map[string]any{"version": 1, "modules": []any{}}},
		{name: "valid-system-selector", valid: true, instance: moduleEntry(map[string]any{
			"path": "90-system.md", "class": "system", "environments": []any{"claude_code", "pi"},
		})},
		{name: "invalid-version", valid: false, instance: withField(valid, "version", 2)},
		{name: "invalid-unknown-entry-field", valid: false, instance: moduleEntry(map[string]any{
			"path": "00-base.md", "chapter": "Base",
		})},
		{name: "invalid-empty-environments", valid: false, instance: moduleEntry(map[string]any{
			"path": "00-base.md", "environments": []any{},
		})},
		{name: "invalid-duplicate-environments", valid: false, instance: moduleEntry(map[string]any{
			"path": "00-base.md", "environments": []any{"claude_code", "claude_code"},
		})},
		{name: "invalid-unknown-class", valid: false, instance: moduleEntry(map[string]any{
			"path": "00-base.md", "class": "global",
		})},
		{name: "invalid-parent-path", valid: false, instance: moduleEntry(map[string]any{
			"path": "../escape.md",
		})},
		{name: "invalid-duplicate-path", valid: false, instance: duplicatePath},
	}
}

func withField(value map[string]any, key string, item any) map[string]any {
	out := cloneMap(value)
	out[key] = item
	return out
}

// orderedObject serializes members in insertion order, unlike a Go map. It
// exists so a negative case can violate the sorted-surface-keys rule of
// environments.md section 8.2, which sorted map serialization cannot express.
type orderedObject struct {
	keys   []string
	values []any
}

func (object *orderedObject) MarshalJSON() ([]byte, error) {
	var buffer bytes.Buffer
	buffer.WriteByte('{')
	for index, key := range object.keys {
		if index > 0 {
			buffer.WriteByte(',')
		}
		encodedKey, err := json.Marshal(key)
		if err != nil {
			return nil, err
		}
		buffer.Write(encodedKey)
		buffer.WriteByte(':')
		encodedValue, err := json.Marshal(object.values[index])
		if err != nil {
			return nil, err
		}
		buffer.Write(encodedValue)
	}
	buffer.WriteByte('}')
	return buffer.Bytes(), nil
}

// orderedSurfaceObject rebuilds a surfaces object in an explicit key order so
// a negative case can violate the sorted-keys rule of section 8.2.
func orderedSurfaceObject(order []string, surfaces map[string]any) *orderedObject {
	object := &orderedObject{}
	for _, key := range order {
		object.keys = append(object.keys, key)
		object.values = append(object.values, surfaces[key])
	}
	return object
}

// writeSnapshotAcquisitionVectors emits conformance/v1/vectors/snapshot-acquisition.json
// and expected/byte-exact-snapshot_sha256.txt: the environments.md section 1.2
// rule that a snapshot of a commit carries exactly the committed blob bytes.
// The hash is the core section 8 content hash over every regular file of the
// fixture tree, .gitattributes included — it is a regular file of that tree.
func writeSnapshotAcquisitionVectors(dir, fixture, expected string) {
	files := regularFiles(fixture)
	hash := contentHash(fixture, files)
	writeText(filepath.Join(expected, "byte-exact-snapshot_sha256.txt"), hash+"\n")
	entries := make([]any, 0, len(files))
	for _, rel := range files {
		payload, err := os.ReadFile(filepath.Join(fixture, filepath.FromSlash(rel)))
		must(err)
		sum := sha256.Sum256(payload)
		entries = append(entries, map[string]any{
			"path":   rel,
			"bytes":  len(payload),
			"sha256": "sha256:" + hex.EncodeToString(sum[:]),
		})
	}
	writeJSON(filepath.Join(dir, "snapshot-acquisition.json"), map[string]any{
		"schema_version":      1,
		"protocol_version":    protocolVersion,
		"capability":          "agent-environments",
		"capability_revision": 1,
		"rule":                "environments.md section 1.2: a snapshot produced from a commit contains, for every regular-file entry of the commit's tree, exactly the committed blob bytes; working-tree conversion and attribute-driven archive processing never alter, add, or omit an entry",
		"cases": []any{
			map[string]any{
				"name":    "byte-exact-snapshot",
				"fixture": "fixtures/byte-exact",
				"files":   entries,
				"acquisition_contract": []any{
					"Commit the fixture tree in a repository so that every blob equals the fixture file bytes listed here and the tree carries the fixture's .gitattributes as a regular file (the in-tree `* text=auto` rule would normalize crlf.txt and mixed.txt on an ordinary `git add`; bypass it, for example with `git hash-object -w --no-filters` and `git update-index --add --cacheinfo`, or an `info/attributes` override of `* -text` during the commit). Verify with `git cat-file -p` before acquiring.",
					"Acquire a snapshot of that commit with `core.autocrlf=true` in effect and again with `core.autocrlf=false`.",
					"Both snapshots MUST contain exactly the five listed regular files, and the core section 8 content hash of each snapshot MUST equal expected_sha256.",
					"The `subst.txt` entry MUST still contain the literal text `$Format:%H$` and `$Format:%h$`; the `crlf.txt` entry MUST contain CRLF line endings; the `mixed.txt` entry MUST contain both LF and CRLF line endings.",
				},
				"expected_sha256": hash,
				"expected":        "expected/byte-exact-snapshot_sha256.txt",
			},
		},
	})
}
