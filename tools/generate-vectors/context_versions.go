package main

// The environments.md section 1.4 version, range, and resolution surfaces
// and the section 1.3 lock canonicalization: strict SemVer 2.0 tags with a
// mandatory v prefix and no build metadata, the closed node-semver-derived
// range grammar with its coercion table and excluded forms, the prerelease
// admission rule, the fixed four-step resolution algorithm with downward
// re-selection, the section 6 effective-weight rules, and the CCJ-1 lock
// hash. Every expected value in vectors/context-versions.json is computed
// here; tools/validate.py recomputes each one independently.

import (
	"errors"
	"fmt"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

// ---------------------------------------------------------------------------
// Versions

type semver struct {
	major, minor, patch int
	prerelease          []string
}

func (v semver) String() string {
	text := fmt.Sprintf("%d.%d.%d", v.major, v.minor, v.patch)
	if len(v.prerelease) > 0 {
		text += "-" + strings.Join(v.prerelease, ".")
	}
	return text
}

func isDigits(text string) bool {
	if text == "" {
		return false
	}
	for _, r := range text {
		if r < '0' || r > '9' {
			return false
		}
	}
	return true
}

// parseNumeric accepts a non-negative decimal without leading zeros.
func parseNumeric(text string) (int, bool) {
	if !isDigits(text) || (len(text) > 1 && text[0] == '0') {
		return 0, false
	}
	value, err := strconv.Atoi(text)
	if err != nil {
		return 0, false
	}
	return value, true
}

func parsePrerelease(text string) ([]string, bool) {
	if text == "" {
		return nil, false
	}
	parts := strings.Split(text, ".")
	for _, part := range parts {
		if part == "" {
			return nil, false
		}
		for _, r := range part {
			if !(r == '-' || (r >= '0' && r <= '9') || (r >= 'A' && r <= 'Z') || (r >= 'a' && r <= 'z')) {
				return nil, false
			}
		}
		if isDigits(part) && len(part) > 1 && part[0] == '0' {
			return nil, false
		}
	}
	return parts, true
}

// parseVersion parses a strict SemVer 2.0 version without build metadata.
func parseVersion(text string) (semver, bool) {
	var v semver
	core := text
	if dash := strings.IndexByte(text, '-'); dash >= 0 {
		core = text[:dash]
		pre, ok := parsePrerelease(text[dash+1:])
		if !ok {
			return v, false
		}
		v.prerelease = pre
	}
	parts := strings.Split(core, ".")
	if len(parts) != 3 {
		return v, false
	}
	var ok bool
	if v.major, ok = parseNumeric(parts[0]); !ok {
		return v, false
	}
	if v.minor, ok = parseNumeric(parts[1]); !ok {
		return v, false
	}
	if v.patch, ok = parseNumeric(parts[2]); !ok {
		return v, false
	}
	return v, true
}

// parseTagVersion parses a version tag: a mandatory v prefix, then a strict
// version. A tag that does not parse is not a version candidate.
func parseTagVersion(tag string) (semver, bool) {
	if !strings.HasPrefix(tag, "v") {
		return semver{}, false
	}
	return parseVersion(tag[1:])
}

func comparePrerelease(a, b []string) int {
	if len(a) == 0 && len(b) == 0 {
		return 0
	}
	if len(a) == 0 {
		return 1
	}
	if len(b) == 0 {
		return -1
	}
	for index := 0; index < len(a) && index < len(b); index++ {
		left, right := a[index], b[index]
		leftNumeric, rightNumeric := isDigits(left), isDigits(right)
		switch {
		case leftNumeric && rightNumeric:
			l, _ := strconv.Atoi(left)
			r, _ := strconv.Atoi(right)
			if l != r {
				if l < r {
					return -1
				}
				return 1
			}
		case leftNumeric:
			return -1
		case rightNumeric:
			return 1
		default:
			if left != right {
				if left < right {
					return -1
				}
				return 1
			}
		}
	}
	if len(a) != len(b) {
		if len(a) < len(b) {
			return -1
		}
		return 1
	}
	return 0
}

func compareVersions(a, b semver) int {
	for _, pair := range [][2]int{{a.major, b.major}, {a.minor, b.minor}, {a.patch, b.patch}} {
		if pair[0] != pair[1] {
			if pair[0] < pair[1] {
				return -1
			}
			return 1
		}
	}
	return comparePrerelease(a.prerelease, b.prerelease)
}

// ---------------------------------------------------------------------------
// Ranges

// comparator is one desugared primitive: an operator and a version, or the
// any comparator that matches every stable version.
type comparator struct {
	op      string // ">=", ">", "<=", "<", "="
	version semver
	any     bool
}

func (c comparator) String() string {
	if c.any {
		return "*"
	}
	return c.op + c.version.String()
}

type comparatorSet []comparator
type versionRange []comparatorSet

var errRangeInvalid = errors.New("range does not parse")

type partialVersion struct {
	parts      [3]int
	present    [3]bool
	prerelease []string
}

// parsePartial parses a version or partial version as node-semver does: a
// component of x, X, or * and everything after it are free.
func parsePartial(text string) (partialVersion, error) {
	var partial partialVersion
	if text == "" {
		return partial, errRangeInvalid
	}
	core := text
	preText := ""
	hasPre := false
	if dash := strings.IndexByte(text, '-'); dash >= 0 {
		core, preText, hasPre = text[:dash], text[dash+1:], true
	}
	parts := strings.Split(core, ".")
	if len(parts) > 3 {
		return partial, errRangeInvalid
	}
	for index, part := range parts {
		if part == "x" || part == "X" || part == "*" {
			break
		}
		value, ok := parseNumeric(part)
		if !ok {
			return partial, errRangeInvalid
		}
		partial.parts[index] = value
		partial.present[index] = true
	}
	if hasPre {
		if !partial.present[2] {
			return partial, errRangeInvalid
		}
		pre, ok := parsePrerelease(preText)
		if !ok {
			return partial, errRangeInvalid
		}
		partial.prerelease = pre
	}
	return partial, nil
}

func (p partialVersion) full() semver {
	return semver{major: p.parts[0], minor: p.parts[1], patch: p.parts[2], prerelease: p.prerelease}
}

func lowestPrerelease(major, minor, patch int) semver {
	return semver{major: major, minor: minor, patch: patch, prerelease: []string{"0"}}
}

// desugarPrimitive expands one primitive into comparators under the section
// 1.4 coercion table.
func desugarPrimitive(text string) (comparatorSet, error) {
	op := ""
	for _, candidate := range []string{">=", "<=", ">", "<", "=", "^", "~"} {
		if strings.HasPrefix(text, candidate) {
			op = candidate
			text = text[len(candidate):]
			break
		}
	}
	p, err := parsePartial(text)
	if err != nil {
		return nil, err
	}
	M, m, pt := p.parts[0], p.parts[1], p.parts[2]
	ge := func(v semver) comparator { return comparator{op: ">=", version: v} }
	lt := func(v semver) comparator { return comparator{op: "<", version: v} }
	switch op {
	case "", "=":
		switch {
		case !p.present[0]:
			return comparatorSet{{any: true}}, nil
		case !p.present[1]:
			return comparatorSet{ge(semver{major: M}), lt(lowestPrerelease(M+1, 0, 0))}, nil
		case !p.present[2]:
			return comparatorSet{ge(semver{major: M, minor: m}), lt(lowestPrerelease(M, m+1, 0))}, nil
		default:
			return comparatorSet{{op: "=", version: p.full()}}, nil
		}
	case ">=":
		if !p.present[0] {
			return comparatorSet{{any: true}}, nil
		}
		return comparatorSet{ge(p.full())}, nil
	case ">":
		switch {
		case !p.present[0]:
			return comparatorSet{lt(lowestPrerelease(0, 0, 0))}, nil
		case !p.present[1]:
			return comparatorSet{ge(semver{major: M + 1})}, nil
		case !p.present[2]:
			return comparatorSet{ge(semver{major: M, minor: m + 1})}, nil
		default:
			return comparatorSet{{op: ">", version: p.full()}}, nil
		}
	case "<":
		switch {
		case !p.present[0]:
			return comparatorSet{lt(lowestPrerelease(0, 0, 0))}, nil
		case !p.present[1]:
			return comparatorSet{lt(lowestPrerelease(M, 0, 0))}, nil
		case !p.present[2]:
			return comparatorSet{lt(lowestPrerelease(M, m, 0))}, nil
		default:
			return comparatorSet{lt(p.full())}, nil
		}
	case "<=":
		switch {
		case !p.present[0]:
			return comparatorSet{{any: true}}, nil
		case !p.present[1]:
			return comparatorSet{lt(lowestPrerelease(M+1, 0, 0))}, nil
		case !p.present[2]:
			return comparatorSet{lt(lowestPrerelease(M, m+1, 0))}, nil
		default:
			return comparatorSet{{op: "<=", version: p.full()}}, nil
		}
	case "^":
		switch {
		case !p.present[0]:
			return comparatorSet{{any: true}}, nil
		case !p.present[1]:
			return comparatorSet{ge(semver{major: M}), lt(lowestPrerelease(M+1, 0, 0))}, nil
		case !p.present[2]:
			if M == 0 {
				return comparatorSet{ge(semver{major: 0, minor: m}), lt(lowestPrerelease(0, m+1, 0))}, nil
			}
			return comparatorSet{ge(semver{major: M, minor: m}), lt(lowestPrerelease(M+1, 0, 0))}, nil
		default:
			switch {
			case M > 0:
				return comparatorSet{ge(p.full()), lt(lowestPrerelease(M+1, 0, 0))}, nil
			case m > 0:
				return comparatorSet{ge(p.full()), lt(lowestPrerelease(0, m+1, 0))}, nil
			default:
				return comparatorSet{ge(p.full()), lt(lowestPrerelease(0, 0, pt+1))}, nil
			}
		}
	case "~":
		switch {
		case !p.present[0]:
			return comparatorSet{{any: true}}, nil
		case !p.present[1]:
			return comparatorSet{ge(semver{major: M}), lt(lowestPrerelease(M+1, 0, 0))}, nil
		case !p.present[2]:
			return comparatorSet{ge(semver{major: M, minor: m}), lt(lowestPrerelease(M, m+1, 0))}, nil
		default:
			return comparatorSet{ge(p.full()), lt(lowestPrerelease(M, m+1, 0))}, nil
		}
	}
	return nil, errRangeInvalid
}

// parseRange parses the closed section 1.4 grammar. `latest` is `*`; hyphen
// ranges and a `v` prefix inside a range are rejected.
func parseRange(text string) (versionRange, error) {
	if text == "latest" {
		text = "*"
	}
	var out versionRange
	for _, setText := range strings.Split(text, "||") {
		setText = strings.TrimSpace(setText)
		if setText == "" {
			return nil, errRangeInvalid
		}
		var set comparatorSet
		for _, primitive := range strings.Fields(setText) {
			comparators, err := desugarPrimitive(primitive)
			if err != nil {
				return nil, err
			}
			set = append(set, comparators...)
		}
		out = append(out, set)
	}
	return out, nil
}

func (c comparator) matches(v semver) bool {
	if c.any {
		return true
	}
	cmp := compareVersions(v, c.version)
	switch c.op {
	case "=":
		return cmp == 0
	case ">":
		return cmp > 0
	case ">=":
		return cmp >= 0
	case "<":
		return cmp < 0
	case "<=":
		return cmp <= 0
	}
	return false
}

// setSatisfies applies every comparator and the prerelease rule: a version
// with a prerelease satisfies a set only when some comparator of the set
// names a prerelease on the same major.minor.patch.
func setSatisfies(set comparatorSet, v semver) bool {
	for _, c := range set {
		if !c.matches(v) {
			return false
		}
	}
	if len(v.prerelease) == 0 {
		return true
	}
	for _, c := range set {
		if !c.any && len(c.version.prerelease) > 0 && c.version.major == v.major && c.version.minor == v.minor && c.version.patch == v.patch {
			return true
		}
	}
	return false
}

func rangeSatisfies(r versionRange, v semver) bool {
	for _, set := range r {
		if setSatisfies(set, v) {
			return true
		}
	}
	return false
}

func rangeJSON(r versionRange) []any {
	sets := make([]any, 0, len(r))
	for _, set := range r {
		items := make([]any, 0, len(set))
		for _, c := range set {
			items = append(items, c.String())
		}
		sets = append(sets, items)
	}
	return sets
}

// ---------------------------------------------------------------------------
// Resolution

// resolutionRequirement is one requirement edge as a manifest declares it.
type resolutionRequirement struct {
	Kind      string `json:"kind"` // context, skill, mcp
	Name      string `json:"name"`
	Source    string `json:"source,omitempty"`
	Form      string `json:"form"` // range, tag, revision
	Value     string `json:"value"`
	Weight    *int   `json:"weight,omitempty"`
	Directory string `json:"directory,omitempty"`
}

type resolutionManifest struct {
	Version  string
	Weight   int
	Weights  map[string]int
	Requires []resolutionRequirement
}

type resolutionPackage struct {
	Kind      string
	Source    string
	Tags      map[string]string // tag name -> commit
	Commits   map[string]*resolutionManifest
	Directory string
}

type resolutionOverlay struct {
	Name      string
	Form      string // range, tag, revision, path
	Value     string
	Weight    *int
	StatePin  string              // path overlays
	Manifest  *resolutionManifest // path overlays
	Directory string
}

type resolutionInput struct {
	Root                 string
	RootForm             string
	RootValue            string
	RootDirectory        string
	Overlays             []resolutionOverlay
	OverlayDefaultWeight int
	Packages             map[string]*resolutionPackage
}

type constraint struct {
	name        string
	kind        string
	requirer    string // "machine" or "<name>@<version>"
	requirerOf  string // requirer package name, "" for machine
	form        string
	value       string
	edgeWeight  *int
	directory   string
	overlayDecl *resolutionOverlay
}

func (c constraint) spelling() string {
	if c.form == "path" {
		return "path"
	}
	return c.form + " " + c.value
}

type selection struct {
	kind      string
	version   *semver
	commit    string
	statePin  string
	source    string
	directory string
	manifest  *resolutionManifest
	overlay   *resolutionOverlay
}

type resolutionError struct {
	diagnostic string
	detail     map[string]any
}

func (e *resolutionError) Error() string { return e.diagnostic }

type resolutionResult struct {
	lock     map[string]any
	warnings []map[string]any
	err      *resolutionError
}

func requirerLabel(name string, version *semver) string {
	if version == nil {
		return name
	}
	return name + "@" + version.String()
}

// resolveClosure runs the section 1.4 algorithm and the section 6 weight
// rules and returns the lock or the first diagnostic.
func resolveClosure(input resolutionInput) resolutionResult {
	var constraints []constraint
	selected := map[string]*selection{}
	ceiling := map[string]*semver{}
	pending := map[string]bool{}
	seen := map[string]bool{}
	var warnings []map[string]any

	// Seed.
	constraints = append(constraints, constraint{name: input.Root, kind: "context", requirer: "machine", form: input.RootForm, value: input.RootValue, directory: input.RootDirectory})
	pending[input.Root] = true
	seen[input.Root] = true
	for index := range input.Overlays {
		overlay := &input.Overlays[index]
		if seen[overlay.Name] {
			return resolutionResult{err: &resolutionError{"environment_composition_invalid", map[string]any{"name": overlay.Name}}}
		}
		seen[overlay.Name] = true
		constraints = append(constraints, constraint{name: overlay.Name, kind: "context", requirer: "machine", form: overlay.Form, value: overlay.Value, directory: overlay.Directory, overlayDecl: overlay})
		pending[overlay.Name] = true
	}

	constraintsOn := func(name string) []constraint {
		var out []constraint
		for _, c := range constraints {
			if c.name == name {
				out = append(out, c)
			}
		}
		return out
	}
	dropAttributed := func(requirer string) {
		var kept []constraint
		for _, c := range constraints {
			if c.requirer == requirer {
				pending[c.name] = true
				continue
			}
			kept = append(kept, c)
		}
		constraints = kept
	}
	conflict := func(name string, cs []constraint, candidates []string) *resolutionError {
		requirers := make([]any, 0, len(cs))
		for _, c := range cs {
			requirers = append(requirers, map[string]any{"requirer": c.requirer, "constraint": c.spelling()})
		}
		if candidates == nil {
			candidates = []string{}
		}
		return &resolutionError{"context_range_conflict", map[string]any{"name": name, "requirers": requirers, "candidates": stringsToAny(candidates)}}
	}

	for len(pending) > 0 {
		names := make([]string, 0, len(pending))
		for name := range pending {
			names = append(names, name)
		}
		sort.Strings(names)
		name := names[0]
		delete(pending, name)
		cs := constraintsOn(name)
		if len(cs) == 0 {
			if sel := selected[name]; sel != nil {
				delete(selected, name)
				dropAttributed(requirerLabel(name, sel.version))
			}
			continue
		}
		kind := cs[0].kind
		var pathDecl *resolutionOverlay
		var exactCommits []string
		var ranges []versionRange
		for _, c := range cs {
			switch c.form {
			case "path":
				pathDecl = c.overlayDecl
			case "range":
				r, err := parseRange(c.value)
				if err != nil {
					return resolutionResult{err: &resolutionError{"profile_source_invalid", map[string]any{"name": name, "range": c.value}}}
				}
				ranges = append(ranges, r)
			case "tag":
				pkg := input.Packages[name]
				commit, ok := pkg.Tags[c.value]
				if !ok {
					return resolutionResult{err: &resolutionError{"profile_source_invalid", map[string]any{"name": name, "tag": c.value}}}
				}
				exactCommits = append(exactCommits, commit)
			case "revision":
				exactCommits = append(exactCommits, c.value)
			}
		}
		var next selection
		next.kind = kind
		var candidateVersions []string
		switch {
		case pathDecl != nil:
			v, _ := parseVersion(pathDecl.Manifest.Version)
			next = selection{kind: kind, version: &v, statePin: pathDecl.StatePin, manifest: pathDecl.Manifest, overlay: pathDecl}
		case len(exactCommits) > 0:
			for _, commit := range exactCommits[1:] {
				if commit != exactCommits[0] {
					return resolutionResult{err: conflict(name, cs, nil)}
				}
			}
			pkg := input.Packages[name]
			commit := exactCommits[0]
			manifest := pkg.Commits[commit]
			var version *semver
			if kind == "skill" {
				// The version of the highest version tag peeling to the commit, or none.
				for tag, tagCommit := range pkg.Tags {
					if tagCommit != commit {
						continue
					}
					if v, ok := parseTagVersion(tag); ok && (version == nil || compareVersions(v, *version) > 0) {
						copied := v
						version = &copied
					}
				}
			} else {
				v, ok := parseVersion(manifest.Version)
				if !ok {
					return resolutionResult{err: &resolutionError{"context_manifest_invalid", map[string]any{"name": name}}}
				}
				version = &v
			}
			for _, r := range ranges {
				if version == nil || !rangeSatisfies(r, *version) {
					considered := []string{}
					if version != nil {
						considered = []string{version.String()}
					}
					return resolutionResult{err: conflict(name, cs, considered)}
				}
			}
			next = selection{kind: kind, version: version, commit: commit, source: pkg.Source, directory: cs[0].directory, manifest: manifest}
		default:
			pkg := input.Packages[name]
			type candidate struct {
				version semver
				commit  string
				tag     string
			}
			var candidates []candidate
			for tag, commit := range pkg.Tags {
				if v, ok := parseTagVersion(tag); ok {
					candidates = append(candidates, candidate{v, commit, tag})
				}
			}
			sort.Slice(candidates, func(i, j int) bool { return compareVersions(candidates[i].version, candidates[j].version) < 0 })
			for _, c := range candidates {
				candidateVersions = append(candidateVersions, c.version.String())
			}
			var chosen *candidate
			for index := len(candidates) - 1; index >= 0; index-- {
				c := candidates[index]
				if cap := ceiling[name]; cap != nil && compareVersions(c.version, *cap) > 0 {
					continue
				}
				admitted := true
				for _, r := range ranges {
					if !rangeSatisfies(r, c.version) {
						admitted = false
						break
					}
				}
				if admitted {
					copied := c
					chosen = &copied
					break
				}
			}
			if chosen == nil {
				return resolutionResult{err: conflict(name, cs, candidateVersions)}
			}
			manifest := pkg.Commits[chosen.commit]
			if kind != "skill" {
				if manifest == nil || manifest.Version != chosen.version.String() {
					declared := ""
					if manifest != nil {
						declared = manifest.Version
					}
					return resolutionResult{err: &resolutionError{"context_version_mismatch", map[string]any{"name": name, "tag": chosen.tag, "manifest_version": declared}}}
				}
			}
			version := chosen.version
			next = selection{kind: kind, version: &version, commit: chosen.commit, source: pkg.Source, directory: cs[0].directory, manifest: manifest}
		}
		for _, c := range cs {
			if c.overlayDecl != nil {
				next.overlay = c.overlayDecl
			}
		}
		if current := selected[name]; current != nil {
			if current.commit == next.commit && current.statePin == next.statePin {
				continue
			}
			dropAttributed(requirerLabel(name, current.version))
		}
		copied := next
		selected[name] = &copied
		if next.version != nil {
			v := *next.version
			ceiling[name] = &v
		}
		if next.manifest != nil {
			label := requirerLabel(name, next.version)
			for _, requirement := range next.manifest.Requires {
				constraints = append(constraints, constraint{name: requirement.Name, kind: requirement.Kind, requirer: label, requirerOf: name, form: requirement.Form, value: requirement.Value, edgeWeight: requirement.Weight, directory: requirement.Directory})
				pending[requirement.Name] = true
			}
		}
	}

	// Check.
	for _, c := range constraints {
		sel := selected[c.name]
		if sel == nil {
			return resolutionResult{err: conflict(c.name, constraintsOn(c.name), nil)}
		}
		if c.form == "range" {
			r, _ := parseRange(c.value)
			if sel.version == nil || !rangeSatisfies(r, *sel.version) {
				return resolutionResult{err: conflict(c.name, constraintsOn(c.name), nil)}
			}
		}
	}

	// Effective weights (section 6).
	root := selected[input.Root]
	rootMap := map[string]int{}
	for key, value := range root.manifest.Weights {
		rootMap[key] = value
	}
	names := make([]string, 0, len(selected))
	for name := range selected {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		sel := selected[name]
		if name != input.Root && sel.kind == "context" && sel.manifest != nil && len(sel.manifest.Weights) > 0 {
			return resolutionResult{err: &resolutionError{"context_weights_not_root", map[string]any{"name": name}}}
		}
	}
	for _, c := range constraints {
		if c.requirerOf == input.Root && c.edgeWeight != nil {
			if _, duplicate := root.manifest.Weights[c.name]; duplicate {
				return resolutionResult{err: &resolutionError{"context_weights_duplicate", map[string]any{"name": c.name}}}
			}
			rootMap[c.name] = *c.edgeWeight
		}
	}
	mapKeys := make([]string, 0, len(root.manifest.Weights))
	for key := range root.manifest.Weights {
		mapKeys = append(mapKeys, key)
	}
	sort.Strings(mapKeys)
	for _, key := range mapKeys {
		if sel := selected[key]; sel == nil || sel.kind != "context" {
			return resolutionResult{err: &resolutionError{"context_weight_unknown", map[string]any{"name": key}}}
		}
	}
	weights := map[string]int{}
	for _, name := range names {
		sel := selected[name]
		if sel.kind != "context" {
			weights[name] = 0
			continue
		}
		weight := 0
		if sel.manifest != nil {
			weight = sel.manifest.Weight
		}
		var edges []constraint
		for _, c := range constraints {
			if c.name == name && c.edgeWeight != nil && c.requirerOf != "" && c.requirerOf != input.Root {
				edges = append(edges, c)
			}
		}
		if len(edges) > 0 {
			agreed := true
			for _, edge := range edges[1:] {
				if *edge.edgeWeight != *edges[0].edgeWeight {
					agreed = false
				}
			}
			if !agreed {
				requirers := make([]any, 0, len(edges))
				for _, edge := range edges {
					requirers = append(requirers, map[string]any{"requirer": edge.requirer, "weight": *edge.edgeWeight})
				}
				detail := map[string]any{"name": name, "requirers": requirers}
				if _, named := rootMap[name]; !named {
					return resolutionResult{err: &resolutionError{"context_weight_conflict", detail}}
				}
				detail["diagnostic"] = "context_weight_conflict"
				warnings = append(warnings, detail)
			} else {
				weight = *edges[0].edgeWeight
			}
		}
		if value, named := rootMap[name]; named {
			weight = value
		}
		if sel.overlay != nil {
			weight = input.OverlayDefaultWeight
			if sel.overlay.Weight != nil {
				weight = *sel.overlay.Weight
			}
		}
		weights[name] = weight
	}

	// Lock.
	members := make([]map[string]any, 0, len(selected))
	for _, name := range names {
		sel := selected[name]
		requiredBy := map[string]bool{}
		for _, c := range constraints {
			if c.name == name && c.requirerOf != "" {
				requiredBy[c.requirerOf] = true
			}
		}
		requirers := make([]string, 0, len(requiredBy))
		for requirer := range requiredBy {
			requirers = append(requirers, requirer)
		}
		sort.Strings(requirers)
		member := map[string]any{
			"kind":        sel.kind,
			"name":        name,
			"weight":      weights[name],
			"required_by": stringsToAny(requirers),
			"overlay":     sel.overlay != nil,
		}
		if sel.statePin != "" {
			member["state_sha256"] = sel.statePin
		} else {
			member["source"] = sel.source
			member["commit"] = sel.commit
			if sel.directory != "" {
				member["directory"] = sel.directory
			}
		}
		if sel.version != nil {
			member["version"] = sel.version.String()
		}
		members = append(members, member)
	}
	sort.SliceStable(members, func(i, j int) bool {
		if members[i]["kind"] != members[j]["kind"] {
			return members[i]["kind"].(string) < members[j]["kind"].(string)
		}
		return members[i]["name"].(string) < members[j]["name"].(string)
	})
	lock := map[string]any{"schema_version": 1, "root": input.Root, "members": mapsToAny(members)}
	if warnings == nil {
		warnings = []map[string]any{}
	}
	return resolutionResult{lock: lock, warnings: warnings}
}

// lockHash is the section 1.3 lock hash: SHA-256 over the CCJ-1 bytes.
func lockHash(lock map[string]any) string {
	return canonicalSHA256(lock)
}

// ---------------------------------------------------------------------------
// Vector fixtures

func intPointer(value int) *int { return &value }

func requirementJSON(requirement resolutionRequirement) map[string]any {
	out := map[string]any{"kind": requirement.Kind, "name": requirement.Name, requirement.Form: requirement.Value}
	if requirement.Source != "" {
		out["source"] = requirement.Source
	}
	if requirement.Weight != nil {
		out["weight"] = *requirement.Weight
	}
	if requirement.Directory != "" {
		out["directory"] = requirement.Directory
	}
	return out
}

func manifestJSON(manifest *resolutionManifest) map[string]any {
	out := map[string]any{"version": manifest.Version, "weight": manifest.Weight}
	if len(manifest.Weights) > 0 {
		weights := map[string]any{}
		for key, value := range manifest.Weights {
			weights[key] = value
		}
		out["weights"] = weights
	}
	requires := make([]any, 0, len(manifest.Requires))
	for _, requirement := range manifest.Requires {
		requires = append(requires, requirementJSON(requirement))
	}
	out["requires"] = requires
	return out
}

func resolutionInputJSON(input resolutionInput) map[string]any {
	install := map[string]any{"name": input.Root, input.RootForm: input.RootValue}
	if input.RootDirectory != "" {
		install["directory"] = input.RootDirectory
	}
	overlays := make([]any, 0, len(input.Overlays))
	for _, overlay := range input.Overlays {
		entry := map[string]any{"name": overlay.Name}
		if overlay.Form == "path" {
			entry["path"] = map[string]any{"state_sha256": overlay.StatePin, "manifest": manifestJSON(overlay.Manifest)}
		} else {
			entry[overlay.Form] = overlay.Value
		}
		if overlay.Weight != nil {
			entry["weight"] = *overlay.Weight
		}
		if overlay.Directory != "" {
			entry["directory"] = overlay.Directory
		}
		overlays = append(overlays, entry)
	}
	packages := map[string]any{}
	for name, pkg := range input.Packages {
		tags := map[string]any{}
		for tag, commit := range pkg.Tags {
			tags[tag] = commit
		}
		commits := map[string]any{}
		for commit, manifest := range pkg.Commits {
			if manifest == nil {
				commits[commit] = nil
			} else {
				commits[commit] = manifestJSON(manifest)
			}
		}
		entry := map[string]any{"kind": pkg.Kind, "source": pkg.Source, "tags": tags, "commits": commits}
		packages[name] = entry
	}
	return map[string]any{
		"install":                install,
		"overlays":               overlays,
		"overlay_default_weight": input.OverlayDefaultWeight,
		"packages":               packages,
	}
}

func hexCommit(digit byte) string { return strings.Repeat(string(digit), 40) }

func contextRequirement(name, form, value string, weight *int) resolutionRequirement {
	return resolutionRequirement{Kind: "context", Name: name, Form: form, Value: value, Weight: weight}
}

// versionedPackage builds a package whose version tags map to distinct
// commits and whose manifests declare the given requirements per version.
func versionedPackage(kind, source string, versions map[string]*resolutionManifest, commitOf func(version string) string) *resolutionPackage {
	pkg := &resolutionPackage{Kind: kind, Source: source, Tags: map[string]string{}, Commits: map[string]*resolutionManifest{}}
	for version, manifest := range versions {
		commit := commitOf(version)
		pkg.Tags["v"+version] = commit
		if manifest != nil && manifest.Version == "" {
			manifest.Version = version
		}
		pkg.Commits[commit] = manifest
	}
	return pkg
}

// commitFor derives a deterministic 40-hex commit for a package/version pair.
func commitFor(name, version string) string {
	digest := sha256Identity([]byte(name + "@" + version))
	return digest[len("sha256:") : len("sha256:")+40]
}

func plainManifest(weight int, requires ...resolutionRequirement) *resolutionManifest {
	return &resolutionManifest{Weight: weight, Requires: requires}
}

// workedExampleInput reproduces Decision 0012 section 9: the companyA iOS
// umbrella with the commits the decision prints.
func workedExampleInput() resolutionInput {
	const umbrella = "companyA-root-context-ios-developer-umbrella"
	const core = "companyA-root-context-core"
	const devCore = "companyA-root-context-developers-core"
	const figma = "companyA-root-context-developers-figma"
	const ios = "companyA-root-context-developers-ios"
	const org = "companyA-root-context-organizational-structure"
	fixed := func(commit string) func(string) string { return func(string) string { return commit } }
	packages := map[string]*resolutionPackage{
		umbrella: versionedPackage("context", "github.com/companyA/root-context-ios-developer-umbrella", map[string]*resolutionManifest{
			"2.3.0": {Weight: 100, Weights: map[string]int{org: 10}, Requires: []resolutionRequirement{
				contextRequirement(core, "range", "^3.0", nil),
				contextRequirement(devCore, "range", "^1.4", nil),
				contextRequirement(ios, "range", ">=2.1 <3", intPointer(60)),
				{Kind: "context", Name: figma, Form: "range", Value: "^1.0", Weight: intPointer(40), Directory: "contexts/figma"},
				{Kind: "skill", Name: "swiftui", Form: "range", Value: "^4"},
				{Kind: "skill", Name: "pdf", Form: "range", Value: "~1.2"},
				{Kind: "mcp", Name: "figma-devmode", Form: "range", Value: "^1"},
			}},
			"2.2.0": {Weight: 100},
		}, func(version string) string {
			if version == "2.3.0" {
				return hexCommit('6')
			}
			return commitFor(umbrella, version)
		}),
		core: versionedPackage("context", "github.com/companyA/root-context-core", map[string]*resolutionManifest{
			"3.0.0": {Requires: []resolutionRequirement{contextRequirement(org, "range", "^1.0", nil)}},
			"3.1.0": {Requires: []resolutionRequirement{contextRequirement(org, "range", "^1.0", nil)}},
			"3.2.1": {Requires: []resolutionRequirement{contextRequirement(org, "range", "^1.0", nil)}},
			"4.0.0": {Requires: []resolutionRequirement{contextRequirement(org, "range", "^1.0", nil)}},
		}, func(version string) string {
			if version == "3.2.1" {
				return hexCommit('1')
			}
			return commitFor(core, version)
		}),
		devCore: versionedPackage("context", "github.com/companyA/root-context-developers-core", map[string]*resolutionManifest{
			"1.6.0": {Weight: 20, Requires: []resolutionRequirement{contextRequirement(core, "range", "^3.1", nil)}},
			"1.4.0": {Weight: 20, Requires: []resolutionRequirement{contextRequirement(core, "range", "^3.0", nil)}},
		}, func(version string) string {
			if version == "1.6.0" {
				return hexCommit('3')
			}
			return commitFor(devCore, version)
		}),
		figma: versionedPackage("context", "github.com/companyA/root-contexts", map[string]*resolutionManifest{
			"1.1.0": {},
			"1.0.0": {},
		}, func(version string) string {
			if version == "1.1.0" {
				return hexCommit('4')
			}
			return commitFor(figma, version)
		}),
		ios: versionedPackage("context", "github.com/companyA/root-context-developers-ios", map[string]*resolutionManifest{
			"2.4.2": {Requires: []resolutionRequirement{{Kind: "skill", Name: "swiftui", Form: "range", Value: "^4.2"}}},
			"3.0.0": {Requires: []resolutionRequirement{{Kind: "skill", Name: "swiftui", Form: "range", Value: "^5"}}},
		}, func(version string) string {
			if version == "2.4.2" {
				return hexCommit('5')
			}
			return commitFor(ios, version)
		}),
		org: versionedPackage("context", "github.com/companyA/root-context-organizational-structure", map[string]*resolutionManifest{
			"1.0.4": {},
			"2.0.0": {},
		}, func(version string) string {
			if version == "1.0.4" {
				return hexCommit('2')
			}
			return commitFor(org, version)
		}),
		"figma-devmode": versionedPackage("mcp", "github.com/companyA/mcp-figma-devmode", map[string]*resolutionManifest{
			"1.2.0": {},
		}, fixed(hexCommit('7'))),
		"pdf": versionedPackage("skill", "github.com/relux-works/skill-pdf", map[string]*resolutionManifest{
			"1.2.5": nil, "1.3.0": nil,
		}, func(version string) string {
			if version == "1.2.5" {
				return hexCommit('8')
			}
			return commitFor("pdf", version)
		}),
		"swiftui": versionedPackage("skill", "github.com/relux-works/skill-swiftui", map[string]*resolutionManifest{
			"4.3.0": nil, "4.1.0": nil, "5.0.0": nil,
		}, func(version string) string {
			if version == "4.3.0" {
				return hexCommit('9')
			}
			return commitFor("swiftui", version)
		}),
	}
	return resolutionInput{
		Root: umbrella, RootForm: "range", RootValue: "^2",
		Overlays: []resolutionOverlay{{
			Name: "personal", Form: "path", StatePin: strings.Repeat("a", 64),
			Manifest: &resolutionManifest{Version: "0.3.0"},
		}},
		OverlayDefaultWeight: 1000,
		Packages:             packages,
	}
}

func simpleInput(root, rootRange string, packages map[string]*resolutionPackage) resolutionInput {
	return resolutionInput{Root: root, RootForm: "range", RootValue: rootRange, OverlayDefaultWeight: 1000, Packages: packages}
}

func ctxPackage(name string, versions map[string]*resolutionManifest) *resolutionPackage {
	return versionedPackage("context", "github.com/example/"+name, versions, func(version string) string { return commitFor(name, version) })
}

func skillPackage(name string, versions ...string) *resolutionPackage {
	manifests := map[string]*resolutionManifest{}
	for _, version := range versions {
		manifests[version] = nil
	}
	return versionedPackage("skill", "github.com/example/skill-"+name, manifests, func(version string) string { return commitFor(name, version) })
}

type resolutionCase struct {
	name        string
	description string
	input       resolutionInput
}

func resolutionCases() []resolutionCase {
	cases := []resolutionCase{
		{"worked-example-default-policy", "Decision 0012 section 9: joint ranges, a root weights map, an edge weight, a path overlay at the default weight, and skill and MCP members", workedExampleInput()},
	}
	cases = append(cases, resolutionCase{"range-conflict-empty-intersection", "two requirers whose ranges intersect in nothing fail context_range_conflict naming both", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "range", "^3", nil), contextRequirement("lib", "range", "^1", nil))}),
		"lib":  ctxPackage("lib", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "range", "^2", nil))}),
		"core": ctxPackage("core", map[string]*resolutionManifest{"2.5.0": {}, "3.1.0": {}}),
	})})
	cases = append(cases, resolutionCase{"downward-reselection", "lib is selected at 2.0.0 first; plugin then adds <2 and lib re-selects downward to the highest remaining candidate not above its previous selection", simpleInput("root", "*", map[string]*resolutionPackage{
		"root":   ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("lib", "range", "*", nil), contextRequirement("plugin", "range", "^1", nil))}),
		"lib":    ctxPackage("lib", map[string]*resolutionManifest{"1.5.0": {}, "1.4.0": {}, "2.0.0": {}}),
		"plugin": ctxPackage("plugin", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("lib", "range", "<2", nil))}),
	})})
	cases = append(cases, resolutionCase{"selection-never-increases", "helper lowers app to 1.0.0 and then leaves the closure when app@1.1.0's requirement on it is dropped; app keeps the lowered selection although the constraint that lowered it is gone", simpleInput("root", "*", map[string]*resolutionPackage{
		"root":   ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("app", "range", "^1", nil), contextRequirement("lib", "range", "*", nil))}),
		"app":    ctxPackage("app", map[string]*resolutionManifest{"1.1.0": plainManifest(0, contextRequirement("helper", "range", "^1", nil)), "1.0.0": {}}),
		"helper": ctxPackage("helper", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("lib", "range", "<2", nil), contextRequirement("app", "range", "<1.1", nil))}),
		"lib":    ctxPackage("lib", map[string]*resolutionManifest{"1.5.0": {}, "2.0.0": {}}),
	})})
	cases = append(cases, resolutionCase{"prerelease-admission", "a prerelease satisfies a range only when a primitive names a prerelease on the same major.minor.patch", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "range", "^2.0.0-rc.0", nil))}),
		"core": ctxPackage("core", map[string]*resolutionManifest{"1.9.0": {}, "2.0.0-rc.1": {}, "2.1.0-rc.1": {}}),
	})})
	cases = append(cases, resolutionCase{"prerelease-excluded-by-latest", "latest is * and selects the highest stable version, never a prerelease of the bound", simpleInput("root", "latest", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": {}, "2.0.0-rc.1": {}, "3.0.0-rc.1": {}}),
	})})
	cases = append(cases, resolutionCase{"exact-constraint-unification", "a tag, a revision peeling to the same commit, and a range that admits its version unify on one commit", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "tag", "v3.2.1", nil), contextRequirement("a", "range", "^1", nil), contextRequirement("b", "range", "^1", nil))}),
		"a":    ctxPackage("a", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "revision", commitFor("core", "3.2.1"), nil))}),
		"b":    ctxPackage("b", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "range", "^3", nil))}),
		"core": ctxPackage("core", map[string]*resolutionManifest{"3.2.1": {}, "3.3.0": {}}),
	})})
	cases = append(cases, resolutionCase{"exact-constraints-disagree", "two exact constraints that peel to different commits fail context_range_conflict", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "tag", "v3.2.1", nil), contextRequirement("a", "range", "^1", nil))}),
		"a":    ctxPackage("a", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "revision", commitFor("core", "3.3.0"), nil))}),
		"core": ctxPackage("core", map[string]*resolutionManifest{"3.2.1": {}, "3.3.0": {}}),
	})})
	cases = append(cases, resolutionCase{"exact-outside-range", "an exact constraint fixes the only candidate, and a range that does not admit its version fails context_range_conflict", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "tag", "v3.2.1", nil), contextRequirement("a", "range", "^1", nil))}),
		"a":    ctxPackage("a", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "range", "^2", nil))}),
		"core": ctxPackage("core", map[string]*resolutionManifest{"2.9.0": {}, "3.2.1": {}}),
	})})
	cases = append(cases, resolutionCase{"or-highest-member", "a || disjunction selects the highest candidate satisfying any member", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "range", "^1 || ^3", nil))}),
		"core": ctxPackage("core", map[string]*resolutionManifest{"1.9.0": {}, "2.0.0": {}, "3.0.0": {}, "3.1.0": {}, "4.0.0": {}}),
	})})
	cases = append(cases, resolutionCase{"latest-is-star", "an install with no requirement flag applies --range latest, which is *", simpleInput("root", "latest", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": {}, "1.2.0": {}, "2.0.0-beta.1": {}}),
	})})
	cases = append(cases, resolutionCase{"no-version-tags", "a source with no version tags satisfies no range; latest finds no candidate", simpleInput("root", "latest", map[string]*resolutionPackage{
		"root": {Kind: "context", Source: "github.com/example/root", Tags: map[string]string{"stable": commitFor("root", "stable")}, Commits: map[string]*resolutionManifest{commitFor("root", "stable"): {Version: "0.9.0"}}},
	})})
	cases = append(cases, resolutionCase{"non-version-tag-exact", "a root pinned by a tag that is not a version takes the manifest version at that commit", resolutionInput{Root: "root", RootForm: "tag", RootValue: "stable", OverlayDefaultWeight: 1000, Packages: map[string]*resolutionPackage{
		"root": {Kind: "context", Source: "github.com/example/root", Tags: map[string]string{"stable": commitFor("root", "stable"), "v0.8.0": commitFor("root", "0.8.0")}, Commits: map[string]*resolutionManifest{commitFor("root", "stable"): {Version: "0.9.0"}, commitFor("root", "0.8.0"): {Version: "0.8.0"}}},
	}}})
	cases = append(cases, resolutionCase{"version-mismatch", "a manifest whose version differs from the version tag it resolved from fails context_version_mismatch", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("core", "range", "^1", nil))}),
		"core": ctxPackage("core", map[string]*resolutionManifest{"1.2.0": {Version: "1.1.0"}}),
	})})
	cases = append(cases, resolutionCase{"skill-exact-dependency", "a skill manifest's own exact dependencies enter as fixed candidates; the skill version is the highest version tag peeling to the pinned commit", simpleInput("root", "*", map[string]*resolutionPackage{
		"root":   ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, resolutionRequirement{Kind: "skill", Name: "render", Form: "range", Value: "^2"}, resolutionRequirement{Kind: "skill", Name: "fonts", Form: "range", Value: ">=1"})}),
		"render": {Kind: "skill", Source: "github.com/example/skill-render", Tags: map[string]string{"v2.0.0": commitFor("render", "2.0.0")}, Commits: map[string]*resolutionManifest{commitFor("render", "2.0.0"): {Requires: []resolutionRequirement{{Kind: "skill", Name: "fonts", Form: "revision", Value: commitFor("fonts", "1.1.0")}}}}},
		"fonts":  {Kind: "skill", Source: "github.com/example/skill-fonts", Tags: map[string]string{"v1.0.0": commitFor("fonts", "1.0.0"), "v1.1.0": commitFor("fonts", "1.1.0"), "release-1.1": commitFor("fonts", "1.1.0"), "v1.2.0": commitFor("fonts", "1.2.0")}, Commits: map[string]*resolutionManifest{}},
	})})
	cases = append(cases, resolutionCase{"weight-conflict", "two direct requirers disagree on a member's edge weight and the root's weights map does not name it: context_weight_conflict", simpleInput("root", "*", map[string]*resolutionPackage{
		"root":   ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("a", "range", "^1", nil), contextRequirement("b", "range", "^1", nil))}),
		"a":      ctxPackage("a", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("shared", "range", "^1", intPointer(30)))}),
		"b":      ctxPackage("b", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("shared", "range", "^1", intPointer(50)))}),
		"shared": ctxPackage("shared", map[string]*resolutionManifest{"1.0.0": {Weight: 5}}),
	})})
	cases = append(cases, resolutionCase{"weight-conflict-root-map-wins", "the same disagreement is a warning when the root's weights map names the member; the root has the final word", simpleInput("root", "*", map[string]*resolutionPackage{
		"root":   ctxPackage("root", map[string]*resolutionManifest{"1.0.0": {Weights: map[string]int{"shared": 70}, Requires: []resolutionRequirement{contextRequirement("a", "range", "^1", nil), contextRequirement("b", "range", "^1", nil)}}}),
		"a":      ctxPackage("a", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("shared", "range", "^1", intPointer(30)))}),
		"b":      ctxPackage("b", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("shared", "range", "^1", intPointer(50)))}),
		"shared": ctxPackage("shared", map[string]*resolutionManifest{"1.0.0": {Weight: 5}}),
	})})
	cases = append(cases, resolutionCase{"weights-not-root", "a non-root member carrying a non-empty weights map fails context_weights_not_root at resolution", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, contextRequirement("a", "range", "^1", nil))}),
		"a":    ctxPackage("a", map[string]*resolutionManifest{"1.0.0": {Weights: map[string]int{"root": 1}}}),
	})})
	cases = append(cases, resolutionCase{"weights-duplicate", "a package named both on a root edge with a weight and in the root's weights map fails context_weights_duplicate", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": {Weights: map[string]int{"a": 10}, Requires: []resolutionRequirement{contextRequirement("a", "range", "^1", intPointer(20))}}}),
		"a":    ctxPackage("a", map[string]*resolutionManifest{"1.0.0": {}}),
	})})
	cases = append(cases, resolutionCase{"weight-unknown", "a root weights entry naming a package outside the closure fails context_weight_unknown", simpleInput("root", "*", map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": {Weights: map[string]int{"absent": 10}, Requires: []resolutionRequirement{contextRequirement("a", "range", "^1", nil)}}}),
		"a":    ctxPackage("a", map[string]*resolutionManifest{"1.0.0": {}}),
	})})
	cases = append(cases, resolutionCase{"overlay-joint-resolution-conflict", "an overlay that needs a skill version the root forbids is a reported context_range_conflict, never a silent second copy", resolutionInput{Root: "root", RootForm: "range", RootValue: "*", OverlayDefaultWeight: 1000, Overlays: []resolutionOverlay{{Name: "personal", Form: "range", Value: "*"}}, Packages: map[string]*resolutionPackage{
		"root":     ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(0, resolutionRequirement{Kind: "skill", Name: "swiftui", Form: "range", Value: "^4"})}),
		"personal": ctxPackage("personal", map[string]*resolutionManifest{"0.3.0": plainManifest(0, resolutionRequirement{Kind: "skill", Name: "swiftui", Form: "range", Value: "^5"})}),
		"swiftui":  skillPackage("swiftui", "4.3.0", "5.0.0"),
	}}})
	cases = append(cases, resolutionCase{"overlay-git-explicit-weight", "a git overlay joins the closure with its declared weight; a member that is both an overlay and a requirement takes the overlay's weight", resolutionInput{Root: "root", RootForm: "range", RootValue: "*", OverlayDefaultWeight: 1000, Overlays: []resolutionOverlay{{Name: "team", Form: "range", Value: "^1", Weight: intPointer(250)}}, Packages: map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": plainManifest(100, contextRequirement("team", "range", "^1", intPointer(40)))}),
		"team": ctxPackage("team", map[string]*resolutionManifest{"1.0.0": {Weight: 10}, "1.1.0": {Weight: 10}}),
	}}})
	cases = append(cases, resolutionCase{"overlay-duplicate-name", "an overlay declaration that repeats a name already declared is environment_composition_invalid", resolutionInput{Root: "root", RootForm: "range", RootValue: "*", OverlayDefaultWeight: 1000, Overlays: []resolutionOverlay{{Name: "root", Form: "range", Value: "*"}}, Packages: map[string]*resolutionPackage{
		"root": ctxPackage("root", map[string]*resolutionManifest{"1.0.0": {}}),
	}}})
	return cases
}

// versionParseCases pin the section 1.4 tag grammar: mandatory v, strict
// SemVer 2.0, no build metadata, no leading zeros.
func versionParseCases() []any {
	tags := []string{
		"v1.2.3", "v0.0.0", "v2.0.0-rc.1", "v1.0.0-alpha.beta", "v10.20.30-0.3.7",
		"1.2.3", "v1.2", "v1.2.3+build.5", "v01.2.3", "v1.2.3-01", "v1.2.3-rc..1", "V1.2.3", "v1.2.3.4", "stable", "v1.2.3-rc_1",
	}
	cases := make([]any, 0, len(tags))
	for _, tag := range tags {
		item := map[string]any{"tag": tag}
		if v, ok := parseTagVersion(tag); ok {
			item["candidate"] = true
			item["version"] = v.String()
			item["major"], item["minor"], item["patch"] = v.major, v.minor, v.patch
			pre := []any{}
			for _, part := range v.prerelease {
				pre = append(pre, part)
			}
			item["prerelease"] = pre
		} else {
			item["candidate"] = false
		}
		cases = append(cases, item)
	}
	return cases
}

func versionOrderingCase() map[string]any {
	input := []string{"1.0.0", "1.0.0-alpha.1", "1.0.0-beta.11", "1.0.0-alpha", "1.0.0-rc.1", "1.0.0-beta.2", "1.0.0-alpha.beta", "1.0.0-beta", "0.9.9", "1.0.1-0", "1.0.1"}
	versions := make([]semver, 0, len(input))
	for _, text := range input {
		v, ok := parseVersion(text)
		if !ok {
			panic("ordering case version does not parse: " + text)
		}
		versions = append(versions, v)
	}
	sort.SliceStable(versions, func(i, j int) bool { return compareVersions(versions[i], versions[j]) < 0 })
	sorted := make([]any, 0, len(versions))
	for _, v := range versions {
		sorted = append(sorted, v.String())
	}
	return map[string]any{"name": "semver-precedence", "input": stringsToAny(input), "expected_ascending": sorted}
}

// rangeParseCases pin the coercion table and the excluded forms.
func rangeParseCases() []any {
	ranges := []string{
		"1.2.3", "=1.2.3", "1.2", "=1.2", "1", ">=2.1", ">1.2", ">1.2.3", "<3", "<1.2", "<1.2.3", "<=1.2", "<=1", "<=1.2.3",
		"^1.2.3", "^0.2.3", "^0.0.3", "^1.4", "^0.1", "^0", "^1.2.3-beta.2",
		"~1.2.3", "~1.2", "~1", "~1.2.3-beta.2",
		"1.x", "1.2.x", "1.X", "1.*", "*", "x", "X", "latest",
		">=1.0.0 <2", "^1 || ^3", "2.0.0 || >=3.1 <4", "^2.0.0-rc.0", ">=2.0.0-rc.0",
		"1.2.3 - 2.3.4", "v1.2.3", "^v1", ">=v1.0.0", "", "||", "^1 ||", "1.2.3.4", "^01.2", ">>1", "1.2.3-", "latest || ^1",
	}
	cases := make([]any, 0, len(ranges))
	for _, text := range ranges {
		item := map[string]any{"range": text}
		if parsed, err := parseRange(text); err == nil {
			item["valid"] = true
			item["comparator_sets"] = rangeJSON(parsed)
		} else {
			item["valid"] = false
			item["error"] = "profile_source_invalid"
		}
		cases = append(cases, item)
	}
	return cases
}

// satisfiesCases pin admission per (range, version), the prerelease rule
// included. Each pair is asserted against node-semver 7.7.4 in the drafting
// report; a pair not checked there is not listed here.
func satisfiesCases() []any {
	pairs := [][2]string{
		{"1.2", "1.2.0"}, {"1.2", "1.2.9"}, {"1.2", "1.3.0"}, {"1.2", "1.3.0-0"},
		{">=2.1", "2.1.0"}, {">=2.1", "2.0.9"}, {">=2.1", "3.0.0"},
		{">1.2", "1.2.9"}, {">1.2", "1.3.0"},
		{"<3", "2.9.9"}, {"<3", "3.0.0"}, {"<3", "3.0.0-rc.1"},
		{"<=1.2", "1.2.9"}, {"<=1.2", "1.3.0"},
		{"^1.2.3", "1.2.3"}, {"^1.2.3", "1.9.0"}, {"^1.2.3", "2.0.0"}, {"^1.2.3", "2.0.0-0"}, {"^1.2.3", "1.2.2"},
		{"^0.2.3", "0.2.9"}, {"^0.2.3", "0.3.0"},
		{"^0.0.3", "0.0.3"}, {"^0.0.3", "0.0.4"},
		{"^1.4", "1.4.0"}, {"^1.4", "1.3.9"}, {"^1.4", "2.0.0"},
		{"^0.1", "0.1.5"}, {"^0.1", "0.2.0"},
		{"^0", "0.9.9"}, {"^0", "1.0.0"},
		{"~1.2.3", "1.2.9"}, {"~1.2.3", "1.3.0"},
		{"~1.2", "1.2.0"}, {"~1.2", "1.3.0"},
		{"~1", "1.9.9"}, {"~1", "2.0.0"},
		{"*", "1.0.0"}, {"*", "2.0.0-rc.1"}, {"latest", "1.0.0"}, {"latest", "2.0.0-rc.1"},
		{"x", "0.0.0"}, {"X", "9.9.9-beta"},
		{">=1.0.0", "2.0.0-rc.1"}, {"<3", "2.0.0-rc.1"},
		{"^2.0.0-rc.0", "2.0.0-rc.1"}, {"^2.0.0-rc.0", "2.1.0-rc.1"}, {"^2.0.0-rc.0", "2.1.0"}, {"^2.0.0-rc.0", "2.0.0-rc.0"}, {"^2.0.0-rc.0", "2.0.0"},
		{">=2.0.0-rc.0", "2.0.0-rc.1"}, {">=2.0.0-rc.0", "2.1.0-rc.1"}, {">=2.0.0-rc.0", "3.0.0"},
		{"^1 || ^3", "3.1.0"}, {"^1 || ^3", "2.0.0"}, {"^1 || ^3", "1.9.0"},
		{">=1.0.0 <2", "1.5.0"}, {">=1.0.0 <2", "2.0.0"}, {">=1.0.0 <2", "2.0.0-0"},
		{"1.2.3", "1.2.3"}, {"1.2.3", "1.2.4"},
		{"~1.2.3-beta.2", "1.2.3-beta.4"}, {"~1.2.3-beta.2", "1.2.4-beta.2"}, {"~1.2.3-beta.2", "1.2.4"},
	}
	cases := make([]any, 0, len(pairs))
	for _, pair := range pairs {
		parsed, err := parseRange(pair[0])
		must(err)
		v, ok := parseVersion(pair[1])
		if !ok {
			panic("satisfies case version does not parse: " + pair[1])
		}
		cases = append(cases, map[string]any{"range": pair[0], "version": pair[1], "satisfies": rangeSatisfies(parsed, v)})
	}
	return cases
}

// lockCanonicalizationCases pin the section 1.3 hash: CCJ-1 bytes of the
// lock, SHA-256, spelled sha256:<hex>.
func lockCanonicalizationCases() []any {
	minimal := map[string]any{
		"schema_version": 1,
		"root":           "solo",
		"members": []any{
			map[string]any{"kind": "context", "name": "solo", "source": "github.com/example/solo", "version": "1.0.0", "commit": fixedCommit, "weight": 0, "required_by": []any{}, "overlay": false},
		},
	}
	pathRoot := map[string]any{
		"schema_version": 1,
		"root":           "authoring",
		"members": []any{
			map[string]any{"kind": "context", "name": "authoring", "version": "0.1.0", "state_sha256": strings.Repeat("cd", 32), "weight": 0, "required_by": []any{}, "overlay": false},
			map[string]any{"kind": "skill", "name": "pdf", "source": "github.com/relux-works/skill-pdf", "commit": hexCommit('8'), "weight": 0, "required_by": []any{"authoring"}, "overlay": false},
		},
	}
	worked := resolveClosure(workedExampleInput())
	if worked.err != nil {
		panic("worked example does not resolve: " + worked.err.diagnostic)
	}
	cases := []any{}
	for _, item := range []struct {
		name string
		lock map[string]any
	}{{"minimal-single-root", minimal}, {"path-root-with-skill", pathRoot}, {"worked-example", worked.lock}} {
		payload := canonicalBytes(item.lock)
		cases = append(cases, map[string]any{
			"name":        item.name,
			"lock":        item.lock,
			"ccj1_bytes":  string(payload),
			"byte_length": len(payload),
			"lock_sha256": lockHash(item.lock),
		})
	}
	return cases
}

// writeContextVersionVectors emits conformance/v1/vectors/context-versions.json.
func writeContextVersionVectors(dir string) {
	resolutions := []any{}
	for _, item := range resolutionCases() {
		result := resolveClosure(item.input)
		entry := map[string]any{
			"name":        item.name,
			"description": item.description,
			"input":       resolutionInputJSON(item.input),
		}
		if result.err != nil {
			entry["expected"] = map[string]any{"error": result.err.diagnostic, "detail": result.err.detail}
		} else {
			entry["expected"] = map[string]any{
				"lock":        result.lock,
				"lock_sha256": lockHash(result.lock),
				"warnings":    mapsToAny(result.warnings),
			}
		}
		resolutions = append(resolutions, entry)
	}
	writeJSON(filepath.Join(dir, "context-versions.json"), map[string]any{
		"schema_version":      1,
		"protocol_version":    protocolVersion,
		"capability":          "agent-environments",
		"capability_revision": 1,
		"range_semantics":     "node-semver 7.7.4 (Caret Ranges, Tilde Ranges, X-Ranges, Prerelease Tags) restricted as environments.md section 1.4 states: no hyphen ranges, no v inside a range, latest is *; the any comparator is spelled * in comparator_sets",
		"version_cases":       versionParseCases(),
		"ordering_cases":      []any{versionOrderingCase()},
		"range_cases":         rangeParseCases(),
		"satisfies_cases":     satisfiesCases(),
		"lock_cases":          lockCanonicalizationCases(),
		"resolution_cases":    resolutions,
	})
}
