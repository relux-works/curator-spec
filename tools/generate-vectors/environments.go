package main

// The agent-environments revision-1 conformance surfaces of
// protocol/environments.md under the Decision 0012 model: the section 5
// emitted order under both precedence primitives, the curator-root-context-v2
// generation header with its lock line, the part-joining and `## Context:`
// chapter rules, the no-chapter member, zero-module and no-context outputs,
// the referenced-form layout grouped per package, the managed opencode.json
// CCJ-1 bytes, the system-prompt output, the section 5.8 MCP launch-channel
// bytes per adapter, and the section 5.6 surface hashes.

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

const (
	environmentHeaderMarker     = "curator-root-context-v2"
	environmentGeneratedLine    = "generated: Curator Protocol environments revision 1 (https://github.com/relux-works/curator-spec)"
	environmentNoticeLine       = "notice: generated file; direct edits are unsupported and are detected as drift; update the source profile repository or its composed profiles instead"
	environmentModulesDirectory = ".agent-context/modules"
	environmentSystemPromptPath = ".agent-context/system-prompt.md"
	environmentCodexMCPPath     = "curator-mcp.config.toml"

	winnerHigherWeight   = "higher-weight"
	winnerLowerWeight    = "lower-weight"
	placementWinnerLast  = "winner-last"
	placementWinnerFirst = "winner-first"
)

// environmentRootTargets maps each revision-1 adapter to its home-relative
// root-context target from environments.md section 7.1.
var environmentRootTargets = map[string]string{
	"claude_code": "CLAUDE.md",
	"codex_cli":   "AGENTS.md",
	"opencode":    "AGENTS.md",
	"pi":          "AGENTS.md",
}

// environmentMCPTargets maps each adapter to its section 5.8 MCP file; pi has
// none.
var environmentMCPTargets = map[string]string{
	"claude_code": ".agent-context/mcp/claude_code.json",
	"codex_cli":   environmentCodexMCPPath,
	"opencode":    ".agent-context/mcp/opencode.json",
}

type precedencePolicy struct {
	winner    string
	placement string
}

var defaultPrecedence = precedencePolicy{winnerHigherWeight, placementWinnerLast}

func (p precedencePolicy) json() map[string]any {
	return map[string]any{"winner": p.winner, "placement": p.placement}
}

type environmentModule struct {
	path         string
	content      string
	class        string   // "" selects the default class root
	environments []string // nil selects every environment
}

// environmentPackage is the snapshot content of one context member.
type environmentPackage struct {
	hasContext bool
	modules    []environmentModule
}

// environmentMember is one lock member together with the names it requires,
// from which the lock's required_by lists are derived.
type environmentMember struct {
	kind      string
	name      string
	source    string
	directory string
	version   string
	commit    string
	state     string
	weight    int
	overlay   bool
	requires  []string
}

func (m environmentMember) pin() string {
	if m.state != "" {
		return "state sha256:" + m.state
	}
	return "commit " + m.commit
}

// mcpServer is the resolved server of one MCP declaration package.
type mcpServer struct {
	transport    string
	command      string
	args         []string
	url          string
	envNames     []string
	environments []string // nil selects every adapter
}

// environmentClosure is the materialization input: a lock's members, the
// module content of each context member, and the servers of each MCP member.
type environmentClosure struct {
	root     string
	members  []environmentMember
	packages map[string]environmentPackage
	servers  map[string]mcpServer
}

func environmentFixtureMembers() map[string]environmentMember {
	return map[string]environmentMember{
		"companyA":     {kind: "context", name: "companyA", source: "github.com/example/companyA", version: "2.3.0", commit: fixedCommit, weight: 100},
		"personal":     {kind: "context", name: "personal", version: "0.3.0", state: strings.Repeat("ab", 32), weight: 1000, overlay: true},
		"emptyoverlay": {kind: "context", name: "emptyoverlay", source: "github.com/example/emptyoverlay", version: "0.1.0", commit: strings.Repeat("1", 40), weight: 1000, overlay: true},
		"emptytoo":     {kind: "context", name: "emptytoo", source: "github.com/example/emptytoo", version: "0.1.0", commit: strings.Repeat("2", 40), weight: 1000, overlay: true},
		"selective":    {kind: "context", name: "selective", source: "github.com/example/selective", version: "1.0.0", commit: strings.Repeat("3", 40)},
		"nocontext":    {kind: "context", name: "nocontext", source: "github.com/example/nocontext", version: "1.0.0", commit: strings.Repeat("4", 40)},
		"default":      {kind: "context", name: "default", version: "0.0.0", state: strings.Repeat("ab", 32)},
		// The weights closure: Decision 0012 section 9 shapes with short names.
		"umbrella": {kind: "context", name: "umbrella", source: "github.com/companyA/root-context-ios-developer-umbrella", version: "2.3.0", commit: strings.Repeat("6", 40), weight: 100, requires: []string{"core", "figma", "ios"}},
		"core":     {kind: "context", name: "core", source: "github.com/companyA/root-context-core", version: "3.2.1", commit: strings.Repeat("1", 40), weight: 0, requires: []string{"org"}},
		"org":      {kind: "context", name: "org", source: "github.com/companyA/root-context-organizational-structure", version: "1.0.4", commit: strings.Repeat("2", 40), weight: 10},
		"ios":      {kind: "context", name: "ios", source: "github.com/companyA/root-context-developers-ios", version: "2.4.2", commit: strings.Repeat("5", 40), weight: 60},
		"figma":    {kind: "context", name: "figma", source: "github.com/companyA/root-contexts", directory: "contexts/figma", version: "1.1.0", commit: strings.Repeat("4", 40), weight: 60},
		// MCP declaration packages.
		"figma-devmode": {kind: "mcp", name: "figma-devmode", source: "github.com/companyA/mcp-figma-devmode", version: "1.2.0", commit: strings.Repeat("7", 40)},
		"docs-remote":   {kind: "mcp", name: "docs-remote", source: "github.com/example/mcp-docs-remote", version: "0.5.0", commit: strings.Repeat("d", 40)},
		"codex-only":    {kind: "mcp", name: "codex-only", source: "github.com/example/mcp-codex-only", version: "1.0.0", commit: strings.Repeat("e", 40)},
	}
}

func environmentFixturePackages() map[string]environmentPackage {
	single := func(name string) environmentPackage {
		return environmentPackage{hasContext: true, modules: []environmentModule{{path: "00-" + name + ".md", content: "# " + strings.ToUpper(name[:1]) + name[1:] + "\n\n" + name + " context.\n"}}}
	}
	return map[string]environmentPackage{
		"companyA": {hasContext: true, modules: []environmentModule{
			{path: "00-base.md", content: "# Base\n\nShared engineering context.\n"},
			{path: "10-style.md", content: "# Style\n\nWrite tersely.\n"},
			{path: "20-claude.md", content: "# Claude\n\nClaude-only guidance.\n", environments: []string{"claude_code"}},
			{path: "90-system.md", content: "You are the companyA reviewer.\n", class: "system"},
		}},
		"personal": {hasContext: true, modules: []environmentModule{
			{path: "00-base.md", content: "# Personal\n\nPersonal overlay context.\n"},
			{path: "90-system.md", content: "Prefer short answers.\n", class: "system"},
		}},
		"emptyoverlay": {hasContext: true},
		"emptytoo":     {hasContext: true},
		"selective": {hasContext: true, modules: []environmentModule{
			{path: "90-system.md", content: "Claude-only system prompt.\n", class: "system", environments: []string{"claude_code"}},
		}},
		"nocontext": {hasContext: false},
		"default": {hasContext: true, modules: []environmentModule{
			{path: "00-base.md", content: "# Default\n\nMigrated machine scope.\n"},
		}},
		"umbrella": single("umbrella"),
		"core":     single("core"),
		"org":      single("org"),
		"ios":      single("ios"),
		"figma":    single("figma"),
	}
}

func environmentFixtureServers() map[string]mcpServer {
	return map[string]mcpServer{
		"figma-devmode": {transport: "stdio", command: "npx", args: []string{"-y", "figma-developer-mcp", "--stdio"}, envNames: []string{"FIGMA_API_KEY"}},
		"docs-remote":   {transport: "http", url: "https://mcp.example.com/docs", envNames: []string{"DOCS_TOKEN", "DOCS_ORG"}, environments: []string{"claude_code", "opencode"}},
		"codex-only":    {transport: "stdio", command: "uvx", args: []string{}, environments: []string{"codex_cli"}},
	}
}

// environmentFixtureClosure assembles a closure from fixture member names:
// the first name is the root, the rest are lock members (overlays or
// requirements as the fixture declares them).
func environmentFixtureClosure(names ...string) environmentClosure {
	members := environmentFixtureMembers()
	packages := environmentFixturePackages()
	servers := environmentFixtureServers()
	closure := environmentClosure{root: names[0], packages: map[string]environmentPackage{}, servers: map[string]mcpServer{}}
	for index, name := range names {
		member, ok := members[name]
		if !ok {
			panic("unknown environment fixture member " + name)
		}
		if index == 0 {
			member.overlay = false
		}
		closure.members = append(closure.members, member)
		if member.kind == "context" {
			closure.packages[name] = packages[name]
		}
		if member.kind == "mcp" {
			closure.servers[name] = servers[name]
			root := &closure.members[0]
			root.requires = append(append([]string{}, root.requires...), name)
		}
	}
	return closure
}

// environmentLock renders the closure as its context-lock-v1 object: members
// sorted by (kind, name), required_by derived from the requirement edges.
func environmentLock(closure environmentClosure) map[string]any {
	requiredBy := map[string][]string{}
	for _, member := range closure.members {
		for _, required := range member.requires {
			requiredBy[required] = append(requiredBy[required], member.name)
		}
	}
	sorted := append([]environmentMember{}, closure.members...)
	sort.SliceStable(sorted, func(i, j int) bool {
		if sorted[i].kind != sorted[j].kind {
			return sorted[i].kind < sorted[j].kind
		}
		return sorted[i].name < sorted[j].name
	})
	members := make([]any, 0, len(sorted))
	for _, member := range sorted {
		requirers := append([]string{}, requiredBy[member.name]...)
		sort.Strings(requirers)
		entry := map[string]any{
			"kind":        member.kind,
			"name":        member.name,
			"version":     member.version,
			"weight":      member.weight,
			"required_by": stringsToAny(requirers),
			"overlay":     member.overlay,
		}
		if member.state != "" {
			entry["state_sha256"] = member.state
		} else {
			entry["source"] = member.source
			entry["commit"] = member.commit
			if member.directory != "" {
				entry["directory"] = member.directory
			}
		}
		members = append(members, entry)
	}
	return map[string]any{"schema_version": 1, "root": closure.root, "members": members}
}

// environmentEmittedOrder computes the section 5 emitted order of the
// closure's context members: the core section 7 Kahn order (a member is
// ready when every context it requires is emitted; the smallest ready name
// goes first), stably sorted by effective weight — ascending under
// winner=higher-weight placement=winner-last, descending under
// winner=lower-weight placement=winner-last, and the reverse under
// placement=winner-first. Ties keep the topological order under every pair.
func environmentEmittedOrder(closure environmentClosure, policy precedencePolicy) []environmentMember {
	byName := map[string]environmentMember{}
	for _, member := range closure.members {
		if member.kind == "context" {
			byName[member.name] = member
		}
	}
	emitted := map[string]bool{}
	var order []environmentMember
	for len(order) < len(byName) {
		var ready []string
		for name, member := range byName {
			if emitted[name] {
				continue
			}
			ok := true
			for _, required := range member.requires {
				if _, isContext := byName[required]; isContext && !emitted[required] {
					ok = false
				}
			}
			if ok {
				ready = append(ready, name)
			}
		}
		if len(ready) == 0 {
			panic("environment closure has a context cycle")
		}
		sort.Strings(ready)
		emitted[ready[0]] = true
		order = append(order, byName[ready[0]])
	}
	ascending := (policy.winner == winnerHigherWeight) == (policy.placement == placementWinnerLast)
	sort.SliceStable(order, func(i, j int) bool {
		if ascending {
			return order[i].weight < order[j].weight
		}
		return order[i].weight > order[j].weight
	})
	return order
}

// environmentHeader renders the section 5.1 generation header part.
func environmentHeader(closure environmentClosure, policy precedencePolicy) string {
	var root environmentMember
	for _, member := range closure.members {
		if member.name == closure.root {
			root = member
		}
	}
	lines := []string{"<!--", environmentHeaderMarker, "root: " + root.name + " " + root.version + " " + root.pin()}
	for _, member := range environmentEmittedOrder(closure, policy) {
		line := "member: " + member.name + " " + member.version + " " + member.pin() + " weight " + strconv.Itoa(member.weight)
		if member.overlay {
			line += " overlay"
		}
		lines = append(lines, line)
	}
	lines = append(lines,
		"precedence: winner="+policy.winner+" placement="+policy.placement,
		"lock: "+lockHash(environmentLock(closure)),
		environmentGeneratedLine, environmentNoticeLine, "-->")
	return strings.Join(lines, "\n") + "\n"
}

// environmentApplicable filters a package's modules of one class for one
// environment under section 3: an absent selector applies everywhere.
func environmentApplicable(pkg environmentPackage, environment, class string) []environmentModule {
	var applicable []environmentModule
	for _, module := range pkg.modules {
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

func environmentChapter(member environmentMember) string {
	return "---\n\n## Context: " + member.name + " " + member.version + "\n"
}

func environmentReferencePath(packageName, modulePath string) string {
	return environmentModulesDirectory + "/" + packageName + "/" + modulePath
}

// environmentRootContextFiles materializes the root-context surface for a
// closure, environment, form, and policy, returning the home-relative file
// set. A false first result means no root-context surface exists (section 2:
// the root declares no context).
func environmentRootContextFiles(closure environmentClosure, environment, form string, policy precedencePolicy) (bool, map[string]string) {
	if !closure.packages[closure.root].hasContext {
		return false, nil
	}
	files := map[string]string{}
	parts := []string{environmentHeader(closure, policy)}
	var instructions []string
	for _, member := range environmentEmittedOrder(closure, policy) {
		modules := environmentApplicable(closure.packages[member.name], environment, "root")
		if len(modules) == 0 {
			continue
		}
		if !(environment == "opencode" && form == "referenced") {
			parts = append(parts, environmentChapter(member))
		}
		for _, module := range modules {
			switch form {
			case "monolithic":
				parts = append(parts, module.content)
			case "referenced":
				reference := environmentReferencePath(member.name, module.path)
				files[reference] = module.content
				instructions = append(instructions, reference)
				if environment != "opencode" {
					parts = append(parts, "@"+reference+"\n")
				}
			default:
				panic("unsupported root-context form " + form)
			}
		}
	}
	if environment == "opencode" && form == "referenced" {
		// Section 5.3: the opencode root file is the header part alone and
		// the managed opencode.json carries the ordered reference list as
		// CCJ-1 bytes followed by exactly one trailing LF.
		files[environmentRootTargets[environment]] = environmentHeader(closure, policy)
		files["opencode.json"] = string(canonicalValue(map[string]any{"instructions": stringsToAny(instructions)})) + "\n"
		return true, files
	}
	files[environmentRootTargets[environment]] = environmentJoin(parts)
	return true, files
}

// environmentSystemPromptFiles materializes the section 5.5 system-prompt
// surface. A false first result means no applicable system module exists and
// the file is absent.
func environmentSystemPromptFiles(closure environmentClosure, environment string, policy precedencePolicy) (bool, map[string]string) {
	var parts []string
	for _, member := range environmentEmittedOrder(closure, policy) {
		for _, module := range environmentApplicable(closure.packages[member.name], environment, "system") {
			parts = append(parts, module.content)
		}
	}
	if len(parts) == 0 {
		return false, nil
	}
	return true, map[string]string{environmentSystemPromptPath: environmentJoin(parts)}
}

// environmentMCPSet is the lock's mcp members whose selector applies to the
// adapter, in sorted name order.
func environmentMCPSet(closure environmentClosure, environment string) []string {
	var names []string
	for _, member := range closure.members {
		if member.kind != "mcp" {
			continue
		}
		server := closure.servers[member.name]
		if server.environments != nil {
			selected := false
			for _, identifier := range server.environments {
				if identifier == environment {
					selected = true
				}
			}
			if !selected {
				continue
			}
		}
		names = append(names, member.name)
	}
	sort.Strings(names)
	return names
}

// tomlBasicString renders a TOML basic string.
func tomlBasicString(value string) string {
	var out strings.Builder
	out.WriteByte('"')
	for _, r := range value {
		switch r {
		case '"':
			out.WriteString(`\"`)
		case '\\':
			out.WriteString(`\\`)
		case '\n':
			out.WriteString(`\n`)
		case '\r':
			out.WriteString(`\r`)
		case '\t':
			out.WriteString(`\t`)
		default:
			if r < 0x20 || r == 0x7f {
				out.WriteString(`\u` + strings.ToUpper(strings.Repeat("0", 4-len(strconv.FormatInt(int64(r), 16)))+strconv.FormatInt(int64(r), 16)))
			} else {
				out.WriteRune(r)
			}
		}
	}
	out.WriteByte('"')
	return out.String()
}

// environmentMCPFiles materializes the section 5.8 MCP launch-channel file for
// an adapter. A false first result means the resolved set is empty or the
// adapter has no MCP file (pi).
func environmentMCPFiles(closure environmentClosure, environment string) (bool, map[string]string) {
	target, ok := environmentMCPTargets[environment]
	if !ok {
		return false, nil
	}
	names := environmentMCPSet(closure, environment)
	if len(names) == 0 {
		return false, nil
	}
	switch environment {
	case "claude_code":
		servers := map[string]any{}
		for _, name := range names {
			server := closure.servers[name]
			if server.transport == "stdio" {
				servers[name] = map[string]any{"args": stringsToAny(server.args), "command": server.command, "type": "stdio"}
			} else {
				servers[name] = map[string]any{"type": "http", "url": server.url}
			}
		}
		return true, map[string]string{target: string(canonicalValue(map[string]any{"mcpServers": servers})) + "\n"}
	case "opencode":
		servers := map[string]any{}
		for _, name := range names {
			server := closure.servers[name]
			if server.transport == "stdio" {
				servers[name] = map[string]any{"command": stringsToAny(append([]string{server.command}, server.args...)), "type": "local"}
			} else {
				servers[name] = map[string]any{"type": "remote", "url": server.url}
			}
		}
		return true, map[string]string{target: string(canonicalValue(map[string]any{"mcp": servers})) + "\n"}
	case "codex_cli":
		var out strings.Builder
		for _, name := range names {
			server := closure.servers[name]
			out.WriteString("[mcp_servers." + name + "]\n")
			if server.transport == "stdio" {
				out.WriteString("command = " + tomlBasicString(server.command) + "\n")
				items := make([]string, 0, len(server.args))
				for _, arg := range server.args {
					items = append(items, tomlBasicString(arg))
				}
				out.WriteString("args = [" + strings.Join(items, ", ") + "]\n")
			} else {
				out.WriteString("url = " + tomlBasicString(server.url) + "\n")
			}
		}
		return true, map[string]string{target: out.String()}
	}
	return false, nil
}

// environmentEnvNames is the sorted union of env_names over an adapter's set.
func environmentEnvNames(closure environmentClosure, environment string) []string {
	union := map[string]bool{}
	for _, name := range environmentMCPSet(closure, environment) {
		for _, envName := range closure.servers[name].envNames {
			union[envName] = true
		}
	}
	names := make([]string, 0, len(union))
	for name := range union {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
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

func environmentPackagesJSON(closure environmentClosure) map[string]any {
	packages := map[string]any{}
	for name, pkg := range closure.packages {
		entry := map[string]any{"has_context": pkg.hasContext}
		if pkg.hasContext {
			modules := make([]any, 0, len(pkg.modules))
			for _, module := range pkg.modules {
				item := map[string]any{"path": module.path, "content": module.content}
				if module.class != "" {
					item["class"] = module.class
				}
				if module.environments != nil {
					item["environments"] = stringsToAny(module.environments)
				}
				modules = append(modules, item)
			}
			entry["modules"] = modules
		}
		packages[name] = entry
	}
	return packages
}

func environmentServersJSON(closure environmentClosure) map[string]any {
	servers := map[string]any{}
	for name, server := range closure.servers {
		entry := map[string]any{"transport": server.transport}
		if server.transport == "stdio" {
			entry["command"] = server.command
			entry["args"] = stringsToAny(server.args)
		} else {
			entry["url"] = server.url
		}
		if server.envNames != nil {
			entry["env_names"] = stringsToAny(server.envNames)
		}
		if server.environments != nil {
			entry["environments"] = stringsToAny(server.environments)
		}
		servers[name] = entry
	}
	return servers
}

func environmentEmittedNames(closure environmentClosure, policy precedencePolicy) []any {
	order := environmentEmittedOrder(closure, policy)
	names := make([]any, 0, len(order))
	for _, member := range order {
		names = append(names, member.name)
	}
	return names
}

func environmentHeaderCase(name string, closure environmentClosure, policy precedencePolicy) map[string]any {
	header := environmentHeader(closure, policy)
	sum := sha256.Sum256([]byte(header))
	lock := environmentLock(closure)
	return map[string]any{
		"name":           name,
		"lock":           lock,
		"lock_sha256":    lockHash(lock),
		"precedence":     policy.json(),
		"emitted_order":  environmentEmittedNames(closure, policy),
		"expected_bytes": header,
		"sha256":         "sha256:" + hex.EncodeToString(sum[:]),
		"line_count":     strings.Count(header, "\n"),
	}
}

// writeEnvironmentVectors emits conformance/v1/vectors/environments.json and
// the byte-exact expected files below conformance/v1/expected/environments.
func writeEnvironmentVectors(dir, expected string) {
	closure := environmentFixtureClosure
	weights := closure("umbrella", "core", "org", "ios", "figma", "personal")
	mcp := closure("companyA", "figma-devmode", "docs-remote", "codex-only")

	headerCases := []any{
		environmentHeaderCase("single-root", closure("companyA"), defaultPrecedence),
		environmentHeaderCase("composed-overlays-default", closure("companyA", "personal", "emptyoverlay"), defaultPrecedence),
		environmentHeaderCase("composed-winner-lower-placement-first", weights, precedencePolicy{winnerLowerWeight, placementWinnerFirst}),
		environmentHeaderCase("local-state-pin", closure("default"), defaultPrecedence),
	}

	type materializationInput struct {
		name        string
		surface     string
		environment string
		form        string
		closure     environmentClosure
		policy      precedencePolicy
	}
	inputs := []materializationInput{
		{"monolithic-claude-code", "root-context", "claude_code", "monolithic", closure("companyA"), defaultPrecedence},
		{"monolithic-codex-selector-excluded", "root-context", "codex_cli", "monolithic", closure("companyA"), defaultPrecedence},
		{"monolithic-composed-no-chapter", "root-context", "claude_code", "monolithic", closure("companyA", "personal", "emptyoverlay"), defaultPrecedence},
		{"monolithic-zero-modules", "root-context", "claude_code", "monolithic", closure("emptyoverlay"), defaultPrecedence},
		{"monolithic-zero-modules-composed", "root-context", "claude_code", "monolithic", closure("emptyoverlay", "emptytoo"), defaultPrecedence},
		{"referenced-claude-code-composed", "root-context", "claude_code", "referenced", closure("companyA", "personal"), defaultPrecedence},
		{"referenced-opencode", "root-context", "opencode", "referenced", closure("companyA"), defaultPrecedence},
		{"referenced-opencode-zero-modules", "root-context", "opencode", "referenced", closure("emptyoverlay"), defaultPrecedence},
		{"no-context-directory", "root-context", "claude_code", "monolithic", closure("nocontext"), defaultPrecedence},
		{"system-prompt-composed", "system-prompt", "claude_code", "", closure("companyA", "personal"), defaultPrecedence},
		{"system-prompt-none-applicable", "system-prompt", "codex_cli", "", closure("selective"), defaultPrecedence},
		{"weights-winner-higher-placement-last", "root-context", "claude_code", "monolithic", weights, precedencePolicy{winnerHigherWeight, placementWinnerLast}},
		{"weights-winner-lower-placement-last", "root-context", "claude_code", "monolithic", weights, precedencePolicy{winnerLowerWeight, placementWinnerLast}},
		{"weights-winner-higher-placement-first", "root-context", "claude_code", "monolithic", weights, precedencePolicy{winnerHigherWeight, placementWinnerFirst}},
		{"weights-winner-lower-placement-first", "root-context", "claude_code", "monolithic", weights, precedencePolicy{winnerLowerWeight, placementWinnerFirst}},
		{"mcp-claude-code", "mcp", "claude_code", "", mcp, defaultPrecedence},
		{"mcp-codex-cli", "mcp", "codex_cli", "", mcp, defaultPrecedence},
		{"mcp-opencode", "mcp", "opencode", "", mcp, defaultPrecedence},
		{"mcp-pi-none", "mcp", "pi", "", mcp, defaultPrecedence},
	}

	materializationCases := make([]any, 0, len(inputs))
	for _, input := range inputs {
		var written bool
		var files map[string]string
		switch input.surface {
		case "system-prompt":
			written, files = environmentSystemPromptFiles(input.closure, input.environment, input.policy)
		case "mcp":
			written, files = environmentMCPFiles(input.closure, input.environment)
		default:
			written, files = environmentRootContextFiles(input.closure, input.environment, input.form, input.policy)
		}
		lock := environmentLock(input.closure)
		item := map[string]any{
			"name":          input.name,
			"surface":       input.surface,
			"environment":   input.environment,
			"precedence":    input.policy.json(),
			"lock":          lock,
			"lock_sha256":   lockHash(lock),
			"packages":      environmentPackagesJSON(input.closure),
			"emitted_order": environmentEmittedNames(input.closure, input.policy),
			"file_written":  written,
			"files":         []any{},
		}
		if input.surface == "root-context" {
			item["form"] = input.form
		}
		if input.surface == "mcp" {
			item["mcp_servers"] = environmentServersJSON(input.closure)
			item["mcp_set"] = stringsToAny(environmentMCPSet(input.closure, input.environment))
			item["env_names"] = stringsToAny(environmentEnvNames(input.closure, input.environment))
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
					"bytes":    len(payload),
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
		"header_type_line":      environmentHeaderMarker,
		"part_rule":             "every part ends with exactly one LF; the document is the parts joined with exactly one additional LF between adjacent parts",
		"emitted_order_rule":    "context members in core section 7 Kahn order (smallest ready name first), stably sorted by effective weight: ascending under winner=higher-weight placement=winner-last, descending under winner=lower-weight placement=winner-last, and reversed under placement=winner-first; ties keep the topological order",
		"header_cases":          headerCases,
		"materialization_cases": materializationCases,
	})
}

// ---------------------------------------------------------------------------
// Schema cases

// validAgentContextV1 is the section 2 positive example: an umbrella root with
// modules, every requirement kind, an edge weight, a directory, and a weights
// map.
func validAgentContextV1() map[string]any {
	return map[string]any{
		"schema_version": 1,
		"name":           "companyA-root-context-ios-developer-umbrella",
		"version":        "2.3.0",
		"weight":         100,
		"context": map[string]any{
			"modules": []any{
				map[string]any{"path": "00-ios-umbrella.md"},
				map[string]any{"path": "90-ios-system.md", "class": "system", "environments": []any{"claude_code"}},
			},
		},
		"requires": map[string]any{
			"contexts": map[string]any{
				"companyA-root-context-core":             map[string]any{"git": "https://github.com/companyA/root-context-core.git", "range": "^3.0"},
				"companyA-root-context-developers-ios":   map[string]any{"git": "https://github.com/companyA/root-context-developers-ios.git", "range": ">=2.1 <3", "weight": 60},
				"companyA-root-context-developers-figma": map[string]any{"git": "https://github.com/companyA/root-contexts.git", "directory": "contexts/figma", "range": "^1.0", "weight": 40},
			},
			"skills": map[string]any{
				"swiftui": map[string]any{"git": "https://github.com/relux-works/skill-swiftui.git", "range": "^4"},
				"pdf":     map[string]any{"git": "https://github.com/relux-works/skill-pdf.git", "range": "~1.2", "mode": "runtime", "commands": []any{"render"}},
			},
			"mcp": map[string]any{
				"figma-devmode": map[string]any{"git": "https://github.com/companyA/mcp-figma-devmode.git", "range": "^1"},
			},
		},
		"weights": map[string]any{"companyA-root-context-organizational-structure": 10},
	}
}

func withContextRequirement(valid map[string]any, kind string, entry map[string]any) map[string]any {
	out := cloneMap(valid)
	out["requires"] = map[string]any{kind: map[string]any{"dependency": entry}}
	return out
}

func withModule(valid map[string]any, entry map[string]any) map[string]any {
	out := cloneMap(valid)
	out["context"] = map[string]any{"modules": []any{entry}}
	return out
}

func agentContextSchemaExamples(valid map[string]any) []schemaExample {
	minimal := map[string]any{"schema_version": 1, "name": "leaf", "version": "1.0.0"}
	umbrellaOnly := map[string]any{"schema_version": 1, "name": "umbrella", "version": "0.1.0", "requires": map[string]any{"contexts": map[string]any{"core": map[string]any{"git": "https://github.com/example/core.git", "tag": "v3.2.1"}}}}
	emptyModules := map[string]any{"schema_version": 1, "name": "role", "version": "1.0.0", "context": map[string]any{"modules": []any{}}}
	revisionRequirement := withContextRequirement(valid, "mcp", map[string]any{"git": "https://github.com/example/mcp.git", "revision": fixedCommit})
	prereleaseVersion := withField(valid, "version", "2.4.0-rc.1")
	emptyWeights := withField(valid, "weights", map[string]any{})

	duplicatePath := withModule(valid, map[string]any{"path": "00-base.md"})
	duplicatePath["context"].(map[string]any)["modules"] = []any{map[string]any{"path": "00-base.md"}, map[string]any{"path": "00-base.md", "class": "system"}}

	return []schemaExample{
		{name: "valid-minimal", valid: true, instance: minimal},
		{name: "valid-pure-umbrella", valid: true, instance: umbrellaOnly},
		{name: "valid-empty-modules", valid: true, instance: emptyModules},
		{name: "valid-revision-requirement", valid: true, instance: revisionRequirement},
		{name: "valid-prerelease-version", valid: true, instance: prereleaseVersion},
		{name: "valid-empty-weights", valid: true, instance: emptyWeights},
		{name: "invalid-schema-version", valid: false, instance: withField(valid, "schema_version", 2)},
		{name: "invalid-unknown-field", valid: false, instance: withField(valid, "agents", []any{"claude_code"})},
		{name: "invalid-missing-version", valid: false, instance: without(valid, "version")},
		{name: "invalid-version-v-prefix", valid: false, instance: withField(valid, "version", "v2.3.0")},
		{name: "invalid-version-build-metadata", valid: false, instance: withField(valid, "version", "2.3.0+build.5")},
		{name: "invalid-version-leading-zero", valid: false, instance: withField(valid, "version", "2.03.0")},
		{name: "invalid-weight-negative", valid: false, instance: withField(valid, "weight", -1)},
		{name: "invalid-weight-above-int32", valid: false, instance: withField(valid, "weight", 2147483648)},
		{name: "invalid-weights-value-string", valid: false, instance: withField(valid, "weights", map[string]any{"core": "10"})},
		{name: "invalid-weights-bad-name", valid: false, instance: withField(valid, "weights", map[string]any{"bad name": 10})},
		{name: "invalid-context-unknown-field", valid: false, instance: withField(valid, "context", map[string]any{"modules": []any{}, "chapter": "Base"})},
		{name: "invalid-context-missing-modules", valid: false, instance: withField(valid, "context", map[string]any{})},
		{name: "invalid-module-unknown-field", valid: false, instance: withModule(valid, map[string]any{"path": "00-base.md", "title": "Base"})},
		{name: "invalid-module-empty-environments", valid: false, instance: withModule(valid, map[string]any{"path": "00-base.md", "environments": []any{}})},
		{name: "invalid-module-duplicate-environments", valid: false, instance: withModule(valid, map[string]any{"path": "00-base.md", "environments": []any{"claude_code", "claude_code"}})},
		{name: "invalid-module-unknown-class", valid: false, instance: withModule(valid, map[string]any{"path": "00-base.md", "class": "global"})},
		{name: "invalid-module-parent-path", valid: false, instance: withModule(valid, map[string]any{"path": "../escape.md"})},
		{name: "invalid-module-duplicate-path", valid: false, instance: duplicatePath},
		{name: "invalid-requires-unknown-kind", valid: false, instance: withField(valid, "requires", map[string]any{"agents": map[string]any{}})},
		{name: "invalid-requirement-two-forms", valid: false, instance: withContextRequirement(valid, "contexts", map[string]any{"git": "https://github.com/example/core.git", "range": "^3", "tag": "v3.2.1"})},
		{name: "invalid-requirement-no-form", valid: false, instance: withContextRequirement(valid, "contexts", map[string]any{"git": "https://github.com/example/core.git"})},
		{name: "invalid-requirement-branch", valid: false, instance: withContextRequirement(valid, "contexts", map[string]any{"git": "https://github.com/example/core.git", "branch": "main"})},
		{name: "invalid-requirement-unknown-field", valid: false, instance: withContextRequirement(valid, "contexts", map[string]any{"git": "https://github.com/example/core.git", "range": "^3", "path": "../core"})},
		{name: "invalid-range-hyphen", valid: false, instance: withContextRequirement(valid, "contexts", map[string]any{"git": "https://github.com/example/core.git", "range": "1.2.3 - 2.3.4"})},
		{name: "invalid-range-v-prefix", valid: false, instance: withContextRequirement(valid, "contexts", map[string]any{"git": "https://github.com/example/core.git", "range": "^v3"})},
		{name: "invalid-range-empty", valid: false, instance: withContextRequirement(valid, "contexts", map[string]any{"git": "https://github.com/example/core.git", "range": ""})},
		{name: "invalid-revision-short", valid: false, instance: withContextRequirement(valid, "contexts", map[string]any{"git": "https://github.com/example/core.git", "revision": "0123456"})},
		{name: "invalid-skill-requirement-directory", valid: false, instance: withContextRequirement(valid, "skills", map[string]any{"git": "https://github.com/example/skill.git", "range": "^1", "directory": "skills/x"})},
		{name: "invalid-skill-commands-without-runtime-mode", valid: false, instance: withContextRequirement(valid, "skills", map[string]any{"git": "https://github.com/example/skill.git", "range": "^1", "commands": []any{"render"}})},
		{name: "invalid-mcp-requirement-weight", valid: false, instance: withContextRequirement(valid, "mcp", map[string]any{"git": "https://github.com/example/mcp.git", "range": "^1", "weight": 10})},
	}
}

// validAgentMCPV1 is the section 2.2 positive example.
func validAgentMCPV1() map[string]any {
	return map[string]any{
		"schema_version": 1,
		"name":           "figma-devmode",
		"version":        "1.2.0",
		"server": map[string]any{
			"transport":    "stdio",
			"command":      "npx",
			"args":         []any{"-y", "figma-developer-mcp", "--stdio"},
			"env_names":    []any{"FIGMA_API_KEY"},
			"environments": []any{"claude_code", "codex_cli", "opencode"},
		},
	}
}

func withServer(valid map[string]any, server map[string]any) map[string]any {
	out := cloneMap(valid)
	out["server"] = server
	return out
}

func agentMCPSchemaExamples(valid map[string]any) []schemaExample {
	stdioMinimal := withServer(valid, map[string]any{"transport": "stdio", "command": "uvx", "args": []any{}})
	httpServer := withServer(valid, map[string]any{"transport": "http", "url": "https://mcp.example.com/docs"})
	httpWithNames := withServer(valid, map[string]any{"transport": "http", "url": "https://mcp.example.com:8443/docs/sse", "env_names": []any{"DOCS_TOKEN"}, "environments": []any{"opencode"}})
	emptyEnvNames := withServer(valid, map[string]any{"transport": "stdio", "command": "npx", "args": []any{"-y", "x"}, "env_names": []any{}})
	return []schemaExample{
		{name: "valid-stdio-minimal", valid: true, instance: stdioMinimal},
		{name: "valid-http", valid: true, instance: httpServer},
		{name: "valid-http-with-env-names-and-selector", valid: true, instance: httpWithNames},
		{name: "valid-empty-env-names", valid: true, instance: emptyEnvNames},
		{name: "invalid-schema-version", valid: false, instance: withField(valid, "schema_version", 2)},
		{name: "invalid-unknown-field", valid: false, instance: withField(valid, "weight", 10)},
		{name: "invalid-missing-server", valid: false, instance: without(valid, "server")},
		{name: "invalid-version-v-prefix", valid: false, instance: withField(valid, "version", "v1.2.0")},
		{name: "invalid-transport", valid: false, instance: withServer(valid, map[string]any{"transport": "sse", "url": "https://mcp.example.com/docs"})},
		{name: "invalid-server-unknown-field", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "npx", "args": []any{}, "env": map[string]any{"FIGMA_API_KEY": "x"}})},
		{name: "invalid-stdio-missing-args", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "npx"})},
		{name: "invalid-stdio-with-url", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "npx", "args": []any{}, "url": "https://mcp.example.com/"})},
		{name: "invalid-command-absolute-path", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "/usr/local/bin/npx", "args": []any{}})},
		{name: "invalid-command-relative-path", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "./bin/server", "args": []any{}})},
		{name: "invalid-command-backslash-path", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "bin\\server.exe", "args": []any{}})},
		{name: "invalid-http-missing-url", valid: false, instance: withServer(valid, map[string]any{"transport": "http"})},
		{name: "invalid-http-with-command", valid: false, instance: withServer(valid, map[string]any{"transport": "http", "url": "https://mcp.example.com/docs", "command": "npx"})},
		{name: "invalid-url-http-scheme", valid: false, instance: withServer(valid, map[string]any{"transport": "http", "url": "http://mcp.example.com/docs"})},
		{name: "invalid-url-userinfo", valid: false, instance: withServer(valid, map[string]any{"transport": "http", "url": "https://user:token@mcp.example.com/docs"})},
		{name: "invalid-url-query", valid: false, instance: withServer(valid, map[string]any{"transport": "http", "url": "https://mcp.example.com/docs?token=x"})},
		{name: "invalid-url-fragment", valid: false, instance: withServer(valid, map[string]any{"transport": "http", "url": "https://mcp.example.com/docs#sse"})},
		{name: "invalid-url-non-ascii-host", valid: false, instance: withServer(valid, map[string]any{"transport": "http", "url": "https://mcp.exämple.com/docs"})},
		{name: "invalid-env-name-reserved-path", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "npx", "args": []any{}, "env_names": []any{"PATH"}})},
		{name: "invalid-env-name-reserved-prefix", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "npx", "args": []any{}, "env_names": []any{"NODE_OPTIONS"}})},
		{name: "invalid-env-name-grammar", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "npx", "args": []any{}, "env_names": []any{"FIGMA API KEY"}})},
		{name: "invalid-env-names-duplicate", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "npx", "args": []any{}, "env_names": []any{"FIGMA_API_KEY", "FIGMA_API_KEY"}})},
		{name: "invalid-environments-empty", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "npx", "args": []any{}, "environments": []any{}})},
		{name: "invalid-environments-duplicate", valid: false, instance: withServer(valid, map[string]any{"transport": "stdio", "command": "npx", "args": []any{}, "environments": []any{"pi", "pi"}})},
	}
}

// validContextLockV1 is the Decision 0012 section 9 lock.
func validContextLockV1() map[string]any {
	result := resolveClosure(workedExampleInput())
	if result.err != nil {
		panic("worked example does not resolve: " + result.err.diagnostic)
	}
	return result.lock
}

func withLockMember(valid map[string]any, index int, mutate func(member map[string]any)) map[string]any {
	out := cloneMap(valid)
	members := out["members"].([]any)
	member := members[index].(map[string]any)
	mutate(member)
	return out
}

func contextLockSchemaExamples(valid map[string]any) []schemaExample {
	single := map[string]any{"schema_version": 1, "root": "solo", "members": []any{
		map[string]any{"kind": "context", "name": "solo", "source": "github.com/example/solo", "version": "1.0.0", "commit": fixedCommit, "weight": 0, "required_by": []any{}, "overlay": false},
	}}
	pathRoot := map[string]any{"schema_version": 1, "root": "authoring", "members": []any{
		map[string]any{"kind": "context", "name": "authoring", "version": "0.1.0", "state_sha256": strings.Repeat("cd", 32), "weight": 0, "required_by": []any{}, "overlay": false},
	}}
	unversionedSkill := map[string]any{"schema_version": 1, "root": "solo", "members": []any{
		map[string]any{"kind": "context", "name": "solo", "source": "github.com/example/solo", "version": "1.0.0", "commit": fixedCommit, "weight": 0, "required_by": []any{}, "overlay": false},
		map[string]any{"kind": "skill", "name": "tools", "source": "github.com/example/tools", "commit": strings.Repeat("9", 40), "weight": 0, "required_by": []any{"solo"}, "overlay": false},
	}}
	// personal is member index 6 in the worked example (context members
	// sorted by name), the umbrella root is index 4.
	unsortedKinds := cloneMap(valid)
	members := unsortedKinds["members"].([]any)
	unsortedKinds["members"] = append([]any{members[len(members)-1]}, members[:len(members)-1]...)
	unsortedNames := cloneMap(valid)
	members = unsortedNames["members"].([]any)
	members[0], members[1] = members[1], members[0]
	unsortedNames["members"] = members
	return []schemaExample{
		{name: "valid-single-root", valid: true, instance: single},
		{name: "valid-path-root", valid: true, instance: pathRoot},
		{name: "valid-unversioned-skill", valid: true, instance: unversionedSkill},
		{name: "invalid-schema-version", valid: false, instance: withField(valid, "schema_version", 2)},
		{name: "invalid-unknown-field", valid: false, instance: withField(valid, "lock_sha256", strings.Repeat("b", 64))},
		{name: "invalid-empty-members", valid: false, instance: withField(valid, "members", []any{})},
		{name: "invalid-member-unknown-field", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { m["source_path"] = "/Users/operator/profiles" })},
		{name: "invalid-member-unknown-kind", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { m["kind"] = "agent" })},
		{name: "invalid-member-both-pins", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { m["state_sha256"] = strings.Repeat("a", 64) })},
		{name: "invalid-member-no-pin", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { delete(m, "commit") })},
		{name: "invalid-path-member-with-source", valid: false, instance: withLockMember(valid, 6, func(m map[string]any) { m["source"] = "github.com/example/personal" })},
		{name: "invalid-path-member-with-directory", valid: false, instance: withLockMember(valid, 6, func(m map[string]any) { m["directory"] = "contexts/personal" })},
		{name: "invalid-path-member-skill-kind", valid: false, instance: withLockMember(valid, 6, func(m map[string]any) { m["kind"] = "skill"; m["overlay"] = false })},
		{name: "invalid-context-without-version", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { delete(m, "version") })},
		{name: "invalid-skill-with-directory", valid: false, instance: withLockMember(valid, 8, func(m map[string]any) { m["directory"] = "skills/pdf" })},
		{name: "invalid-skill-overlay", valid: false, instance: withLockMember(valid, 8, func(m map[string]any) { m["overlay"] = true })},
		{name: "invalid-source-with-git-suffix", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { m["source"] = "github.com/companyA/root-context-ios-developer-umbrella.git" })},
		{name: "invalid-source-uppercase-host", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { m["source"] = "GitHub.com/companyA/root-context-ios-developer-umbrella" })},
		{name: "invalid-weight-negative", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { m["weight"] = -1 })},
		{name: "invalid-required-by-duplicate", valid: false, instance: withLockMember(valid, 0, func(m map[string]any) {
			m["required_by"] = []any{"companyA-root-context-core", "companyA-root-context-core"}
		})},
		{name: "invalid-required-by-unsorted", valid: false, instance: withLockMember(valid, 0, func(m map[string]any) {
			m["required_by"] = []any{"companyA-root-context-ios-developer-umbrella", "companyA-root-context-developers-core"}
		})},
		{name: "invalid-required-by-unknown-member", valid: false, instance: withLockMember(valid, 0, func(m map[string]any) { m["required_by"] = []any{"absent"} })},
		{name: "invalid-root-not-a-member", valid: false, instance: withField(valid, "root", "absent")},
		{name: "invalid-root-with-requirers", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { m["required_by"] = []any{"personal"} })},
		{name: "invalid-root-flagged-overlay", valid: false, instance: withLockMember(valid, 4, func(m map[string]any) { m["overlay"] = true })},
		{name: "invalid-members-unsorted-by-kind", valid: false, instance: unsortedKinds},
		{name: "invalid-members-unsorted-by-name", valid: false, instance: unsortedNames},
		{name: "invalid-members-duplicate", valid: false, instance: withField(valid, "members", append(append([]any{}, valid["members"].([]any)...), valid["members"].([]any)[0]))},
	}
}

// validEnvironmentMarkerV1 is the positive .agent-environment.json example: a
// managed claude_code home of a composed git profile under the default policy.
func validEnvironmentMarkerV1() map[string]any {
	return map[string]any{
		"version": 1,
		"profile": map[string]any{
			"name":        "companyA",
			"root":        "companyA",
			"kind":        "git",
			"lock_sha256": strings.Repeat("b", 64),
			"source":      "github.com/example/companyA",
			"requirement": map[string]any{"range": "^2"},
		},
		"members": []any{
			map[string]any{"name": "companyA", "version": "2.3.0", "commit": fixedCommit, "weight": 100, "overlay": false},
			map[string]any{"name": "personal", "version": "0.3.0", "state_sha256": strings.Repeat("ab", 32), "weight": 1000, "overlay": true, "source_path": "/Users/operator/personal-context"},
		},
		"precedence": map[string]any{"winner": "higher-weight", "placement": "winner-last"},
		"mode":       "managed-home",
		"surfaces": map[string]any{
			"mcp": map[string]any{
				"paths":          []any{".agent-context/mcp/claude_code.json"},
				"content_sha256": "sha256:" + strings.Repeat("2", 64),
				"copies":         []any{},
			},
			"root-context": map[string]any{
				"paths":          []any{"CLAUDE.md"},
				"form":           "monolithic",
				"content_sha256": "sha256:" + strings.Repeat("0", 64),
				"copies":         []any{map[string]any{"path": "CLAUDE.md", "reason": "claude-code-root-context"}},
			},
			"skills": map[string]any{
				"paths":          []any{},
				"content_sha256": "sha256:" + strings.Repeat("1", 64),
				"copies":         []any{},
			},
			"system-prompt": map[string]any{
				"paths":          []any{".agent-context/system-prompt.md"},
				"content_sha256": "sha256:" + strings.Repeat("3", 64),
				"copies":         []any{},
			},
		},
		"passthrough":     []any{},
		"seeds":           []any{".claude.json"},
		"seeded_projects": []any{"/Users/operator/projects/app"},
	}
}

func withProfile(valid map[string]any, profile map[string]any) map[string]any {
	out := cloneMap(valid)
	out["profile"] = profile
	return out
}

func withMarkerMode(valid map[string]any, mode string) map[string]any {
	out := cloneMap(valid)
	out["mode"] = mode
	delete(out, "passthrough")
	delete(out, "seeds")
	delete(out, "seeded_projects")
	if mode == "copied" {
		for _, entry := range out["surfaces"].(map[string]any) {
			delete(entry.(map[string]any), "copies")
		}
	}
	return out
}

func environmentMarkerSchemaExamples(valid map[string]any) []schemaExample {
	localProfile := withProfile(valid, map[string]any{"name": "default", "root": "default", "kind": "local", "lock_sha256": strings.Repeat("c", 64)})
	localProfile["members"] = []any{map[string]any{"name": "default", "version": "0.0.0", "state_sha256": strings.Repeat("ab", 32), "weight": 0, "overlay": false}}

	pathProfile := withProfile(valid, map[string]any{"name": "authoring", "root": "authoring", "kind": "path", "lock_sha256": strings.Repeat("d", 64), "source_path": "/Users/operator/profiles"})
	pathProfile["members"] = []any{map[string]any{"name": "authoring", "version": "0.1.0", "state_sha256": strings.Repeat("cd", 32), "weight": 0, "overlay": false, "source_path": "/Users/operator/profiles"}}

	importedPathProfile := cloneMap(pathProfile)
	importedPathProfile["profile"].(map[string]any)["name"] = "imported"
	importedPathProfile["profile"].(map[string]any)["imported_from_native"] = true

	gitTagWithDirectory := withProfile(valid, map[string]any{"name": "companyA", "root": "companyA", "kind": "git", "lock_sha256": strings.Repeat("b", 64), "source": "github.com/example/companyA", "requirement": map[string]any{"tag": "v2.3.0"}, "directory": "contexts/companyA"})
	gitRevision := withProfile(valid, map[string]any{"name": "companyA", "root": "companyA", "kind": "git", "lock_sha256": strings.Repeat("b", 64), "source": "github.com/example/companyA", "requirement": map[string]any{"revision": fixedCommit}})

	linked := withMarkerMode(valid, "linked")
	linked["surfaces"].(map[string]any)["skills"].(map[string]any)["copies"] = []any{map[string]any{"path": "skills/pdf", "reason": "symlink-fallback"}}
	copied := withMarkerMode(valid, "copied")

	seededParent := cloneMap(valid)
	seededParent["seed_links"] = []any{"git", "gh"}
	passthroughLinked := cloneMap(valid)
	passthroughLinked["passthrough"] = []any{map[string]any{"path": "auth.json", "strategy": "file-link"}}
	delete(passthroughLinked, "seeded_projects")

	return []schemaExample{
		{name: "valid-local-profile", valid: true, instance: localProfile},
		{name: "valid-path-profile", valid: true, instance: pathProfile},
		{name: "valid-imported-path-profile", valid: true, instance: importedPathProfile},
		{name: "valid-git-tag-with-directory", valid: true, instance: gitTagWithDirectory},
		{name: "valid-git-revision", valid: true, instance: gitRevision},
		{name: "valid-linked-symlink-fallback", valid: true, instance: linked},
		{name: "valid-copied", valid: true, instance: copied},
		{name: "valid-seeded-opencode-parent", valid: true, instance: seededParent},
		{name: "valid-passthrough-file-link", valid: true, instance: passthroughLinked},
		{name: "invalid-version", valid: false, instance: withField(valid, "version", 2)},
		{name: "invalid-unknown-field", valid: false, instance: withField(valid, "environment", "claude_code")},
		{name: "invalid-missing-precedence", valid: false, instance: without(valid, "precedence")},
		{name: "invalid-precedence-string", valid: false, instance: withField(valid, "precedence", "later-overrides-earlier")},
		{name: "invalid-precedence-unknown-winner", valid: false, instance: withField(valid, "precedence", map[string]any{"winner": "heavier", "placement": "winner-last"})},
		{name: "invalid-precedence-unknown-field", valid: false, instance: withField(valid, "precedence", map[string]any{"winner": "higher-weight", "placement": "winner-last", "direction": "later-overrides-earlier"})},
		{name: "invalid-profile-unknown-field", valid: false, instance: withProfile(valid, withField(valid["profile"].(map[string]any), "commit", fixedCommit))},
		{name: "invalid-profile-missing-lock", valid: false, instance: withProfile(valid, without(valid["profile"].(map[string]any), "lock_sha256"))},
		{name: "invalid-profile-lock-prefixed", valid: false, instance: withProfile(valid, withField(valid["profile"].(map[string]any), "lock_sha256", "sha256:"+strings.Repeat("b", 64)))},
		{name: "invalid-git-without-requirement", valid: false, instance: withProfile(valid, without(valid["profile"].(map[string]any), "requirement"))},
		{name: "invalid-git-requirement-branch", valid: false, instance: withProfile(valid, withField(valid["profile"].(map[string]any), "requirement", map[string]any{"branch": "main"}))},
		{name: "invalid-git-requirement-two-forms", valid: false, instance: withProfile(valid, withField(valid["profile"].(map[string]any), "requirement", map[string]any{"range": "^2", "tag": "v2.3.0"}))},
		{name: "invalid-git-with-source-path", valid: false, instance: withProfile(valid, withField(valid["profile"].(map[string]any), "source_path", "/Users/operator/profiles"))},
		{name: "invalid-local-with-source", valid: false, instance: withProfile(localProfile, withField(localProfile["profile"].(map[string]any), "source", "github.com/example/default"))},
		{name: "invalid-path-missing-source-path", valid: false, instance: withProfile(pathProfile, without(pathProfile["profile"].(map[string]any), "source_path"))},
		{name: "invalid-path-imported-from-native-false", valid: false, instance: withProfile(pathProfile, withField(pathProfile["profile"].(map[string]any), "imported_from_native", false))},
		{name: "invalid-members-empty", valid: false, instance: withField(valid, "members", []any{})},
		{name: "invalid-member-unknown-field", valid: false, instance: withField(valid, "members", []any{map[string]any{"name": "companyA", "version": "2.3.0", "commit": fixedCommit, "weight": 100, "overlay": false, "kind": "context"}})},
		{name: "invalid-member-both-pins", valid: false, instance: withField(valid, "members", []any{map[string]any{"name": "companyA", "version": "2.3.0", "commit": fixedCommit, "state_sha256": strings.Repeat("ab", 32), "weight": 100, "overlay": false}})},
		{name: "invalid-member-commit-with-source-path", valid: false, instance: withField(valid, "members", []any{map[string]any{"name": "companyA", "version": "2.3.0", "commit": fixedCommit, "weight": 100, "overlay": false, "source_path": "/x"}})},
		{name: "invalid-member-root-missing", valid: false, instance: withField(valid, "members", []any{map[string]any{"name": "personal", "version": "0.3.0", "state_sha256": strings.Repeat("ab", 32), "weight": 1000, "overlay": true}})},
		{name: "invalid-member-duplicate", valid: false, instance: withField(valid, "members", append(append([]any{}, valid["members"].([]any)...), valid["members"].([]any)[0]))},
		{name: "invalid-mode", valid: false, instance: withField(valid, "mode", "adopted")},
		{name: "invalid-surface-unknown-field", valid: false, instance: withField(valid, "surfaces", map[string]any{"root-context": map[string]any{"paths": []any{"CLAUDE.md"}, "content_sha256": "sha256:" + strings.Repeat("0", 64), "copies": []any{}, "copy_fallback": true}})},
		{name: "invalid-surface-missing-paths", valid: false, instance: withField(valid, "surfaces", map[string]any{"root-context": map[string]any{"content_sha256": "sha256:" + strings.Repeat("0", 64), "copies": []any{}}})},
		{name: "invalid-surface-unknown-form", valid: false, instance: withField(valid, "surfaces", map[string]any{"root-context": map[string]any{"paths": []any{"CLAUDE.md"}, "form": "linked", "content_sha256": "sha256:" + strings.Repeat("0", 64), "copies": []any{}}})},
		{name: "invalid-copy-unknown-reason", valid: false, instance: withField(valid, "surfaces", map[string]any{"root-context": map[string]any{"paths": []any{"CLAUDE.md"}, "content_sha256": "sha256:" + strings.Repeat("0", 64), "copies": []any{map[string]any{"path": "CLAUDE.md", "reason": "operator-preference"}}}})},
		{name: "invalid-managed-home-missing-copies", valid: false, instance: withField(valid, "surfaces", map[string]any{"root-context": map[string]any{"paths": []any{"CLAUDE.md"}, "content_sha256": "sha256:" + strings.Repeat("0", 64)}})},
		{name: "invalid-copied-with-copies", valid: false, instance: withField(copied, "surfaces", map[string]any{"root-context": map[string]any{"paths": []any{"CLAUDE.md"}, "content_sha256": "sha256:" + strings.Repeat("0", 64), "copies": []any{}}})},
		{name: "invalid-surfaces-unsorted", valid: false, instance: withField(valid, "surfaces", orderedSurfaceObject([]string{"skills", "root-context", "mcp", "system-prompt"}, valid["surfaces"].(map[string]any)))},
		{name: "invalid-managed-home-missing-passthrough", valid: false, instance: without(valid, "passthrough")},
		{name: "invalid-managed-home-missing-seeds", valid: false, instance: without(valid, "seeds")},
		{name: "invalid-passthrough-unknown-strategy", valid: false, instance: withField(valid, "passthrough", []any{map[string]any{"path": "auth.json", "strategy": "copy"}})},
		{name: "invalid-linked-with-passthrough", valid: false, instance: withField(linked, "passthrough", []any{})},
		{name: "invalid-linked-with-seeds", valid: false, instance: withField(linked, "seeds", []any{})},
		{name: "invalid-seed-links-on-linked-home", valid: false, instance: withField(linked, "seed_links", []any{"git"})},
		{name: "invalid-seeded-projects-on-copied", valid: false, instance: withField(copied, "seeded_projects", []any{"/tmp"})},
		{name: "invalid-seeded-projects-unsorted", valid: false, instance: withField(valid, "seeded_projects", []any{"/Users/operator/projects/b", "/Users/operator/projects/a"})},
	}
}

// adapterSystemPromptChannels reproduces the section 7.3 descriptors.
func adapterSystemPromptChannels(environment string) []any {
	switch environment {
	case "claude_code":
		return []any{
			map[string]any{"kind": "flag", "semantics": "append", "flag": "--append-system-prompt-file", "argument": "path"},
			map[string]any{"kind": "flag", "semantics": "replace", "flag": "--system-prompt-file", "argument": "path"},
		}
	case "codex_cli":
		return []any{map[string]any{"kind": "config-key", "semantics": "replace", "key": "model_instructions_file"}}
	case "opencode":
		return []any{}
	case "pi":
		return []any{
			map[string]any{"kind": "flag", "semantics": "append", "flag": "--append-system-prompt", "argument": "path"},
			map[string]any{"kind": "file", "semantics": "append", "filename": "APPEND_SYSTEM.md"},
			map[string]any{"kind": "file", "semantics": "replace", "filename": "SYSTEM.md"},
		}
	}
	panic("unknown environment " + environment)
}

// adapterMCPChannel reproduces the section 7.8 descriptor; nil for pi.
func adapterMCPChannel(environment string) []any {
	switch environment {
	case "claude_code":
		return []any{map[string]any{"kind": "flag", "flag": "--mcp-config", "argument": "path", "with": []any{"--strict-mcp-config"}}}
	case "codex_cli":
		return []any{map[string]any{"kind": "flag", "flag": "-p", "argument": "name", "name": "curator-mcp"}}
	case "opencode":
		return []any{map[string]any{"kind": "variable", "variable": "OPENCODE_CONFIG"}}
	}
	return nil
}

var adapterHomeVariables = map[string]string{
	"claude_code": "CLAUDE_CONFIG_DIR",
	"codex_cli":   "CODEX_HOME",
	"opencode":    "XDG_CONFIG_HOME",
	"pi":          "PI_CODING_AGENT_DIR",
}

// validLaunchEnvFragmentV1 is the section 10.2 positive example.
func validLaunchEnvFragmentV1() map[string]any {
	return launchFragmentFor("claude_code", true, true)
}

func launchFragmentFor(environment string, systemPrompt, mcp bool) map[string]any {
	home := "/manager/environments/companyA/" + environment
	if environment == "opencode" {
		home = "/manager/environments/companyA/opencode/opencode"
	}
	envValue := "/manager/environments/companyA/" + environment
	fragment := map[string]any{
		"fragment":    "launch-env-fragment-v1",
		"environment": environment,
		"profile":     map[string]any{"name": "companyA", "lock_sha256": strings.Repeat("b", 64)},
		"precedence":  map[string]any{"winner": "higher-weight", "placement": "winner-last"},
		"env":         map[string]any{adapterHomeVariables[environment]: envValue},
	}
	if systemPrompt {
		fragment["system_prompt"] = map[string]any{"path": home + "/.agent-context/system-prompt.md", "channels": adapterSystemPromptChannels(environment)}
	}
	if mcp {
		path := home + "/" + environmentMCPTargets[environment]
		fragment["mcp"] = map[string]any{"path": path, "env_names": []any{"FIGMA_API_KEY"}, "channels": adapterMCPChannel(environment)}
	}
	return fragment
}

func withChannel(valid map[string]any, section string, index int, mutate func(channel map[string]any)) map[string]any {
	out := cloneMap(valid)
	channels := out[section].(map[string]any)["channels"].([]any)
	mutate(channels[index].(map[string]any))
	return out
}

func launchEnvFragmentSchemaExamples(valid map[string]any) []schemaExample {
	return []schemaExample{
		{name: "valid-minimal", valid: true, instance: launchFragmentFor("claude_code", false, false)},
		{name: "valid-system-prompt-only", valid: true, instance: launchFragmentFor("claude_code", true, false)},
		{name: "valid-mcp-only", valid: true, instance: launchFragmentFor("claude_code", false, true)},
		{name: "valid-codex-config-key-and-name-channel", valid: true, instance: launchFragmentFor("codex_cli", true, true)},
		{name: "valid-opencode-empty-channels-and-variable", valid: true, instance: launchFragmentFor("opencode", true, true)},
		{name: "valid-pi-file-channels", valid: true, instance: launchFragmentFor("pi", true, false)},
		{name: "valid-winner-first", valid: true, instance: withField(valid, "precedence", map[string]any{"winner": "lower-weight", "placement": "winner-first"})},
		{name: "valid-path-prepend", valid: true, instance: withField(valid, "path_prepend", "/manager/environments/companyA/bin")},
		{name: "invalid-fragment-identity", valid: false, instance: withField(valid, "fragment", "launch-env-fragment-v2")},
		{name: "invalid-unknown-environment", valid: false, instance: withField(valid, "environment", "cursor")},
		{name: "invalid-unknown-field", valid: false, instance: withField(valid, "composition", []any{})},
		{name: "invalid-missing-precedence", valid: false, instance: without(valid, "precedence")},
		{name: "invalid-precedence-string", valid: false, instance: withField(valid, "precedence", "later-overrides-earlier")},
		{name: "invalid-profile-commit-pin", valid: false, instance: withField(valid, "profile", map[string]any{"name": "companyA", "commit": fixedCommit})},
		{name: "invalid-profile-lock-prefixed", valid: false, instance: withField(valid, "profile", map[string]any{"name": "companyA", "lock_sha256": "sha256:" + strings.Repeat("b", 64)})},
		{name: "invalid-profile-unknown-field", valid: false, instance: withField(valid, "profile", map[string]any{"name": "companyA", "lock_sha256": strings.Repeat("b", 64), "kind": "git"})},
		{name: "invalid-env-empty", valid: false, instance: withField(valid, "env", map[string]any{})},
		{name: "invalid-env-lowercase-variable", valid: false, instance: withField(valid, "env", map[string]any{"claude_config_dir": "/manager/environments/companyA/claude_code"})},
		{name: "invalid-env-wrong-adapter-variable", valid: false, instance: withField(valid, "env", map[string]any{"CODEX_HOME": "/manager/environments/companyA/claude_code"})},
		{name: "invalid-env-two-variables", valid: false, instance: withField(valid, "env", map[string]any{"CLAUDE_CONFIG_DIR": "/manager/environments/companyA/claude_code", "CODEX_HOME": "/manager/environments/companyA/codex_cli"})},
		{name: "invalid-env-relative-path", valid: false, instance: withField(valid, "env", map[string]any{"CLAUDE_CONFIG_DIR": "environments/companyA/claude_code"})},
		{name: "invalid-system-prompt-unknown-field", valid: false, instance: withField(valid, "system_prompt", map[string]any{"path": "/m/system-prompt.md", "channels": []any{}, "contents": "x"})},
		{name: "invalid-system-prompt-missing-channels", valid: false, instance: withField(valid, "system_prompt", map[string]any{"path": "/m/system-prompt.md"})},
		{name: "invalid-system-prompt-channels-not-registry", valid: false, instance: withChannel(valid, "system_prompt", 0, func(c map[string]any) { c["flag"] = "--append-system-prompt" })},
		{name: "invalid-channel-unknown-kind", valid: false, instance: withChannel(valid, "system_prompt", 0, func(c map[string]any) { c["kind"] = "env-file" })},
		{name: "invalid-channel-unknown-semantics", valid: false, instance: withChannel(valid, "system_prompt", 0, func(c map[string]any) { c["semantics"] = "prepend" })},
		{name: "invalid-channel-missing-semantics", valid: false, instance: withChannel(valid, "system_prompt", 0, func(c map[string]any) { delete(c, "semantics") })},
		{name: "invalid-flag-missing-argument", valid: false, instance: withChannel(valid, "system_prompt", 0, func(c map[string]any) { delete(c, "argument") })},
		{name: "invalid-flag-unknown-argument", valid: false, instance: withChannel(valid, "system_prompt", 0, func(c map[string]any) { c["argument"] = "file" })},
		{name: "invalid-flag-name-without-name-argument", valid: false, instance: withChannel(valid, "system_prompt", 0, func(c map[string]any) { c["name"] = "curator" })},
		{name: "invalid-flag-name-argument-without-name", valid: false, instance: withChannel(launchFragmentFor("codex_cli", true, true), "mcp", 0, func(c map[string]any) { delete(c, "name") })},
		{name: "invalid-flag-with-filename", valid: false, instance: withChannel(valid, "system_prompt", 0, func(c map[string]any) { delete(c, "flag"); c["filename"] = "APPEND_SYSTEM.md" })},
		{name: "invalid-flag-empty-with", valid: false, instance: withChannel(valid, "mcp", 0, func(c map[string]any) { c["with"] = []any{} })},
		{name: "invalid-channel-unknown-field", valid: false, instance: withChannel(valid, "mcp", 0, func(c map[string]any) { c["value"] = "/tmp/mcp.json" })},
		{name: "invalid-mcp-channel-with-semantics", valid: false, instance: withChannel(valid, "mcp", 0, func(c map[string]any) { c["semantics"] = "append" })},
		{name: "invalid-mcp-channel-not-registry", valid: false, instance: withChannel(valid, "mcp", 0, func(c map[string]any) { delete(c, "with") })},
		{name: "invalid-mcp-unknown-field", valid: false, instance: withField(valid, "mcp", withField(valid["mcp"].(map[string]any), "env", map[string]any{"FIGMA_API_KEY": "x"}))},
		{name: "invalid-mcp-missing-env-names", valid: false, instance: withField(valid, "mcp", without(valid["mcp"].(map[string]any), "env_names"))},
		{name: "invalid-mcp-env-names-unsorted", valid: false, instance: withField(valid, "mcp", withField(valid["mcp"].(map[string]any), "env_names", []any{"FIGMA_API_KEY", "DOCS_TOKEN"}))},
		{name: "invalid-mcp-env-names-reserved", valid: false, instance: withField(valid, "mcp", withField(valid["mcp"].(map[string]any), "env_names", []any{"HOME"}))},
		{name: "invalid-mcp-two-channels", valid: false, instance: withField(valid, "mcp", withField(valid["mcp"].(map[string]any), "channels", append(append([]any{}, adapterMCPChannel("claude_code")...), adapterMCPChannel("claude_code")...)))},
		{name: "invalid-mcp-on-pi", valid: false, instance: withField(launchFragmentFor("pi", true, false), "mcp", valid["mcp"])},
		{name: "invalid-path-prepend-relative", valid: false, instance: withField(valid, "path_prepend", "environments/companyA/bin")},
		{name: "invalid-path-prepend-outside-root", valid: false, instance: withField(valid, "path_prepend", "/usr/local/bin")},
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
