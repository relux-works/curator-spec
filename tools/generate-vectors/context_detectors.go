package main

// The environments.md section 9.1 audit classes for context and MCP
// snapshots: the deterministic, unpinnable `context-secret-material`
// detector with its closed pattern classes and scoped waivers, and the
// always-warn `context-system-module-present` surfacing class. Every
// expected finding in vectors/context-detectors.json is computed here;
// tools/validate.py recomputes each one from the case's file bytes.

import (
	"encoding/json"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// detectorPattern is one closed pattern class of the secret-material
// detector. The match group named by `group` is the secret body whose byte
// span the finding reports.
type detectorPattern struct {
	class   string
	pattern string
	group   int
	prefix  string // fixed prefix of the body that the placeholder rule skips
}

// The pattern classes are closed: a manager MUST report exactly these and
// MUST NOT report a class this list does not name. A match whose body, after
// the class's fixed prefix, is a single repeated character or ends in EXAMPLE
// is a placeholder, not a finding.
var detectorPatterns = []detectorPattern{
	{"aws-access-key-id", `(?:^|[^A-Z0-9])(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)`, 1, "AKIA"},
	{"private-key-block", `(-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----)`, 1, ""},
	{"bearer-token", `(?:^|[^A-Za-z0-9])Bearer[ \t]+([A-Za-z0-9._~+/-]{20,}=*)`, 1, ""},
}

var detectorRegexps = func() []*regexp.Regexp {
	out := make([]*regexp.Regexp, 0, len(detectorPatterns))
	for _, item := range detectorPatterns {
		out = append(out, regexp.MustCompile(item.pattern))
	}
	return out
}()

// detectorScope names the files the detector reads in a snapshot: every
// context module below context/, the two package manifests, and CONTEXT.md.
func detectorInScope(path string) bool {
	return strings.HasPrefix(path, "context/") || path == "agent-context.json" || path == "agent-mcp.json" || path == "CONTEXT.md"
}

func isPlaceholder(body string) bool {
	if strings.HasSuffix(body, "EXAMPLE") {
		return true
	}
	for index := 1; index < len(body); index++ {
		if body[index] != body[0] {
			return false
		}
	}
	return true
}

type secretWaiver struct {
	Pin    string `json:"pin"`
	File   string `json:"file"`
	Span   [2]int `json:"span"`
	Reason string `json:"reason"`
}

type detectorFinding struct {
	File    string
	Pattern string
	Span    [2]int
	Waived  bool
	Reason  string
}

// detectSecretMaterial runs the closed pattern classes over the in-scope
// files of a snapshot and applies the scoped waivers recorded for its pin.
func detectSecretMaterial(pin string, files map[string]string, waivers []secretWaiver) (findings []detectorFinding, unmatched []secretWaiver) {
	paths := make([]string, 0, len(files))
	for path := range files {
		if detectorInScope(path) {
			paths = append(paths, path)
		}
	}
	sort.Strings(paths)
	matched := map[int]bool{}
	for _, path := range paths {
		content := files[path]
		var fileFindings []detectorFinding
		for index, expression := range detectorRegexps {
			for _, location := range expression.FindAllStringSubmatchIndex(content, -1) {
				start, end := location[2*detectorPatterns[index].group], location[2*detectorPatterns[index].group+1]
				if isPlaceholder(strings.TrimPrefix(content[start:end], detectorPatterns[index].prefix)) {
					continue
				}
				fileFindings = append(fileFindings, detectorFinding{File: path, Pattern: detectorPatterns[index].class, Span: [2]int{start, end}})
			}
		}
		sort.SliceStable(fileFindings, func(i, j int) bool {
			if fileFindings[i].Span[0] != fileFindings[j].Span[0] {
				return fileFindings[i].Span[0] < fileFindings[j].Span[0]
			}
			return fileFindings[i].Pattern < fileFindings[j].Pattern
		})
		for _, finding := range fileFindings {
			for index, waiver := range waivers {
				if waiver.Pin == pin && waiver.File == finding.File && waiver.Span == finding.Span {
					finding.Waived = true
					finding.Reason = waiver.Reason
					matched[index] = true
				}
			}
			findings = append(findings, finding)
		}
	}
	for index, waiver := range waivers {
		if !matched[index] {
			unmatched = append(unmatched, waiver)
		}
	}
	return findings, unmatched
}

// systemModuleWarnings reports every class: system module of a context
// manifest with its package, path, and selector.
func systemModuleWarnings(files map[string]string) []map[string]any {
	manifestText, ok := files["agent-context.json"]
	if !ok {
		return nil
	}
	var manifest struct {
		Name    string `json:"name"`
		Context *struct {
			Modules []struct {
				Path         string   `json:"path"`
				Class        string   `json:"class"`
				Environments []string `json:"environments"`
			} `json:"modules"`
		} `json:"context"`
	}
	must(json.Unmarshal([]byte(manifestText), &manifest))
	if manifest.Context == nil {
		return nil
	}
	var warnings []map[string]any
	for _, module := range manifest.Context.Modules {
		if module.Class != "system" {
			continue
		}
		entry := map[string]any{"class": "context-system-module-present", "package": manifest.Name, "path": module.Path}
		if module.Environments == nil {
			entry["selector"] = nil
		} else {
			entry["selector"] = stringsToAny(module.Environments)
		}
		warnings = append(warnings, entry)
	}
	return warnings
}

type detectorCase struct {
	name        string
	description string
	kind        string
	pin         string
	contentPin  bool
	files       map[string]string
	waivers     []secretWaiver
}

func contextManifestText(name string, modules ...map[string]any) string {
	manifest := map[string]any{"schema_version": 1, "name": name, "version": "1.0.0"}
	if modules != nil {
		manifest["context"] = map[string]any{"modules": stringsToAnyMaps(modules)}
	}
	return string(canonicalValue(manifest)) + "\n"
}

func stringsToAnyMaps(values []map[string]any) []any {
	out := make([]any, 0, len(values))
	for _, value := range values {
		out = append(out, value)
	}
	return out
}

func mcpManifestText(server map[string]any) string {
	return string(canonicalValue(map[string]any{"schema_version": 1, "name": "figma-devmode", "version": "1.2.0", "server": server})) + "\n"
}

func detectorCases() []detectorCase {
	const awsKey = "AKIAJ7Q3ZX9PLM2RT5WQ"
	const bearer = "Bearer eyJhbGciOiJIUzI1NiJ9.c2VjcmV0LXBheWxvYWQtZm9yLXZlY3Rvcg.QmFkSWRlYVRvQ29tbWl0"
	pin := "commit " + fixedCommit
	baseManifest := contextManifestText("companyA", map[string]any{"path": "00-base.md"})
	return []detectorCase{
		{"secret-aws-access-key", "an AWS access key id in a context module is a blocking finding naming the file and the byte span", "context", pin, false, map[string]string{
			"agent-context.json": baseManifest,
			"context/00-base.md": "# Base\n\nUse the deploy role: " + awsKey + " when publishing.\n",
		}, nil},
		{"secret-private-key-block", "a PEM private-key block header in CONTEXT.md is a blocking finding", "context", pin, false, map[string]string{
			"agent-context.json": baseManifest,
			"context/00-base.md": "# Base\n",
			"CONTEXT.md":         "# About\n\n-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAA\n-----END OPENSSH PRIVATE KEY-----\n",
		}, nil},
		{"secret-bearer-token", "a bearer token in a context module is a blocking finding", "context", pin, false, map[string]string{
			"agent-context.json": baseManifest,
			"context/00-base.md": "# Base\n\nAuthorization: " + bearer + "\n",
		}, nil},
		{"secret-in-mcp-args", "agent-mcp.json args are inside the detector scope: a token in an argument is a blocking finding like a token in a module", "mcp", pin, false, map[string]string{
			"agent-mcp.json": mcpManifestText(map[string]any{"transport": "stdio", "command": "npx", "args": []any{"-y", "figma-developer-mcp", "--stdio", "--token", awsKey}}),
		}, nil},
		{"secret-in-mcp-url", "agent-mcp.json url is inside the detector scope: a token embedded in the URL path is a blocking finding", "mcp", pin, false, map[string]string{
			"agent-mcp.json": mcpManifestText(map[string]any{"transport": "http", "url": "https://mcp.example.com/v1/" + awsKey + "/sse"}),
		}, nil},
		{"placeholder-example-key", "a placeholder body — the documented EXAMPLE suffix or one repeated character — is not a finding", "context", pin, false, map[string]string{
			"agent-context.json": baseManifest,
			"context/00-base.md": "# Base\n\nFormat: AKIAIOSFODNN7EXAMPLE or AKIAXXXXXXXXXXXXXXXX; never a real key.\nToken: Bearer <token>\n",
		}, nil},
		{"content-hash-not-secret", "a content hash, a commit id, and a lock hash are not secret material under any closed class", "context", pin, false, map[string]string{
			"agent-context.json": baseManifest,
			"context/00-base.md": "# Base\n\nPinned at sha256:" + strings.Repeat("ab", 32) + " and commit " + fixedCommit + ".\n",
		}, nil},
		{"file-outside-scope-ignored", "a file the manifest does not name and the detector scope does not list is inert", "context", pin, false, map[string]string{
			"agent-context.json": baseManifest,
			"context/00-base.md": "# Base\n",
			"notes/scratch.txt":  "AKIAJ7Q3ZX9PLM2RT5WQ\n",
		}, nil},
		{"waived-span-clears-only-itself", "a scoped waiver clears exactly the finding whose file and span it names at that pin, reported as a warning; the second finding stays blocking", "context", pin, false, map[string]string{
			"agent-context.json": baseManifest,
			"context/00-base.md": "# Base\n\nLegacy: " + awsKey + "\nCurrent: AKIAQ2W8E7R6T5Y4U3I2\n",
		}, []secretWaiver{{Pin: pin, File: "context/00-base.md", Span: [2]int{16, 36}, Reason: "rotated 2026-08-01; documented for history"}}},
		{"waiver-at-other-pin-does-not-apply", "a waiver recorded for another pin matches nothing: the finding blocks and the waiver is context_secret_waiver_unmatched", "context", pin, false, map[string]string{
			"agent-context.json": baseManifest,
			"context/00-base.md": "# Base\n\nLegacy: " + awsKey + "\n",
		}, []secretWaiver{{Pin: "commit " + strings.Repeat("f", 40), File: "context/00-base.md", Span: [2]int{16, 36}, Reason: "waived at the previous pin"}}},
		{"pin-does-not-clear-finding", "the detector is unpinnable: a manager section 7 content-hash pin on the snapshot leaves the finding blocking", "context", pin, true, map[string]string{
			"agent-context.json": baseManifest,
			"context/00-base.md": "# Base\n\nLegacy: " + awsKey + "\n",
		}, nil},
		{"system-module-present", "every class: system module is reported with its package, path, and selector as a warning that never blocks", "context", pin, false, map[string]string{
			"agent-context.json":   contextManifestText("companyA", map[string]any{"path": "00-base.md"}, map[string]any{"path": "90-system.md", "class": "system", "environments": []any{"claude_code"}}, map[string]any{"path": "95-review.md", "class": "system"}),
			"context/00-base.md":   "# Base\n",
			"context/90-system.md": "You are the companyA reviewer.\n",
			"context/95-review.md": "Prefer short answers.\n",
		}, nil},
	}
}

func detectorCaseJSON(item detectorCase) map[string]any {
	findings, unmatched := detectSecretMaterial(item.pin, item.files, item.waivers)
	findingEntries := make([]any, 0, len(findings))
	blocking := false
	warnings := []any{}
	for _, finding := range findings {
		entry := map[string]any{
			"class":    "context-secret-material",
			"pattern":  finding.Pattern,
			"file":     finding.File,
			"span":     []any{finding.Span[0], finding.Span[1]},
			"severity": "blocking",
			"waived":   finding.Waived,
		}
		if finding.Waived {
			entry["waiver_reason"] = finding.Reason
			warnings = append(warnings, map[string]any{"diagnostic": "context_secret_waiver_applied", "file": finding.File, "span": []any{finding.Span[0], finding.Span[1]}, "reason": finding.Reason})
		} else {
			blocking = true
		}
		findingEntries = append(findingEntries, entry)
	}
	for _, waiver := range unmatched {
		warnings = append(warnings, map[string]any{"diagnostic": "context_secret_waiver_unmatched", "pin": waiver.Pin, "file": waiver.File, "span": []any{waiver.Span[0], waiver.Span[1]}})
	}
	for _, warning := range systemModuleWarnings(item.files) {
		warnings = append(warnings, warning)
	}
	files := map[string]any{}
	for path, content := range item.files {
		files[path] = content
	}
	waivers := make([]any, 0, len(item.waivers))
	for _, waiver := range item.waivers {
		waivers = append(waivers, map[string]any{"pin": waiver.Pin, "file": waiver.File, "span": []any{waiver.Span[0], waiver.Span[1]}, "reason": waiver.Reason})
	}
	return map[string]any{
		"name":             item.name,
		"description":      item.description,
		"package_kind":     item.kind,
		"pin":              item.pin,
		"content_hash_pin": item.contentPin,
		"files":            files,
		"waivers":          waivers,
		"expected": map[string]any{
			"findings": findingEntries,
			"warnings": warnings,
			"installs": !blocking,
		},
	}
}

// writeContextDetectorVectors emits conformance/v1/vectors/context-detectors.json.
func writeContextDetectorVectors(dir string) {
	patterns := make([]any, 0, len(detectorPatterns))
	for _, item := range detectorPatterns {
		patterns = append(patterns, map[string]any{"pattern": item.class, "regexp": item.pattern, "group": item.group, "placeholder_prefix": item.prefix})
	}
	cases := []any{}
	for _, item := range detectorCases() {
		cases = append(cases, detectorCaseJSON(item))
	}
	writeJSON(filepath.Join(dir, "context-detectors.json"), map[string]any{
		"schema_version":      1,
		"protocol_version":    protocolVersion,
		"capability":          "agent-environments",
		"capability_revision": 1,
		"scope":               []any{"context/**", "agent-context.json", "agent-mcp.json", "CONTEXT.md"},
		"pattern_classes":     patterns,
		"placeholder_rule":    "a match whose body, after the class's placeholder_prefix, is one repeated character or ends in EXAMPLE is a placeholder and is not reported",
		"span_rule":           "byte offsets into the file, start inclusive and end exclusive, over the reported pattern group",
		"cases":               cases,
	})
}
