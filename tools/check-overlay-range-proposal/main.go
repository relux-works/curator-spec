// Command check-overlay-range-proposal checks bounded synthetic proposal metadata.
// It never resolves Git refs, executes an installer or validates a whole lock.
package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"unicode"
	"unicode/utf8"
)

type tag struct {
	Name     string `json:"name"`
	Commit   string `json:"commit"`
	Manifest string `json:"manifest_version"`
}

type pin struct {
	Directory string `json:"directory"`
	Tag       string `json:"tag"`
	Commit    string `json:"commit"`
	Version   string `json:"version"`
}

type result struct {
	Reason  string `json:"reason"`
	Tag     string `json:"tag"`
	Commit  string `json:"commit"`
	Version string `json:"version"`
	Warning bool   `json:"warning"`
}

type vector struct {
	ID             string `json:"id"`
	Claim          string `json:"claim"`
	Phase          string `json:"phase"`
	Directory      string `json:"directory"`
	Range          string `json:"range"`
	Tags           []tag  `json:"tags"`
	Lock           *pin   `json:"lock"`
	ObservedCommit string `json:"observed_commit"`
	Strict         bool   `json:"strict"`
	Want           result `json:"want"`
}

var stableRE = regexp.MustCompile(`^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`)
var commitRE = regexp.MustCompile(`^[0-9a-f]{40}([0-9a-f]{24})?$`)
var idRE = regexp.MustCompile(`^[a-z0-9][a-z0-9-]{0,79}$`)

func stable(s string) ([3]int64, bool) {
	var v [3]int64
	m := stableRE.FindStringSubmatch(s)
	if m == nil {
		return v, false
	}
	for i := range v {
		n, err := strconv.ParseInt(m[i+1], 10, 64)
		if err != nil {
			return v, false
		}
		v[i] = n
	}
	return v, true
}

func greater(a, b [3]int64) bool {
	for i := range a {
		if a[i] != b[i] {
			return a[i] > b[i]
		}
	}
	return false
}

func directoryOK(s string) bool {
	if s == "" {
		return true // omitted directory: snapshot root
	}
	if !utf8.ValidString(s) || len(s) > 4096 || strings.ContainsAny(s, "\\:") {
		return false
	}
	for _, r := range s {
		if unicode.IsControl(r) {
			return false
		}
	}
	for _, c := range strings.Split(s, "/") {
		if c == "" || c == "." || c == ".." || strings.HasSuffix(c, ".") || strings.HasSuffix(c, " ") {
			return false
		}
		b := strings.ToUpper(strings.SplitN(c, ".", 2)[0])
		if b == "CON" || b == "PRN" || b == "AUX" || b == "NUL" ||
			(len(b) == 4 && (strings.HasPrefix(b, "COM") || strings.HasPrefix(b, "LPT")) && b[3] >= '1' && b[3] <= '9') {
			return false
		}
	}
	return true
}

func safeTag(s string) bool {
	if !utf8.ValidString(s) || len(s) == 0 || len(s) > 255 || s == "@" ||
		strings.ContainsAny(s, " ~^:?*[\\") || strings.Contains(s, "..") || strings.Contains(s, "@{") || strings.HasSuffix(s, ".") {
		return false
	}
	for _, r := range s {
		if r < 32 || r == 127 {
			return false
		}
	}
	for _, c := range strings.Split(s, "/") {
		if c == "" || strings.HasPrefix(c, ".") || strings.HasSuffix(c, ".lock") {
			return false
		}
	}
	return true
}

func prefix(directory string) string {
	if directory == "" {
		return "v"
	}
	return directory + "/v"
}

// evaluate models only the two stable ranges used by this proposal corpus.
// Reasons are model verdicts; strict_tag_refused is not a new public diagnostic.
func evaluate(v vector) result {
	refuse := func(s string) result { return result{Reason: s} }
	if !directoryOK(v.Directory) || !safeTag(prefix(v.Directory)+"0.0.0") {
		return refuse("profile_source_invalid")
	}
	if v.Phase == "replay" {
		p := v.Lock
		if p == nil || p.Directory != v.Directory || !commitRE.MatchString(p.Commit) {
			return refuse("lock_invalid")
		}
		_, ok := stable(p.Version)
		if !ok || p.Tag != prefix(v.Directory)+p.Version || !safeTag(p.Tag) {
			return refuse("lock_invalid")
		}
		moved := v.ObservedCommit != "" && v.ObservedCommit != p.Commit
		if moved && v.Strict {
			return refuse("strict_tag_refused")
		}
		return result{"accept", p.Tag, p.Commit, p.Version, moved}
	}
	if v.Phase != "resolve" || (v.Range != "*" && v.Range != ">=0.1.17 <1.0.0") {
		return refuse("unsupported_fixture")
	}
	var best *tag
	var bv [3]int64
	for i := range v.Tags {
		t := &v.Tags[i]
		if !safeTag(t.Name) || !strings.HasPrefix(t.Name, prefix(v.Directory)) {
			continue
		}
		n, ok := stable(strings.TrimPrefix(t.Name, prefix(v.Directory)))
		if !ok {
			continue
		}
		if v.Range != "*" && (n[0] != 0 || (!greater(n, [3]int64{0, 1, 17}) && n != [3]int64{0, 1, 17})) {
			continue
		}
		if best == nil || greater(n, bv) {
			best, bv = t, n
		}
	}
	if best == nil {
		return refuse("context_range_conflict")
	}
	if !commitRE.MatchString(best.Commit) {
		return refuse("object_invalid")
	}
	wantVersion := strings.TrimPrefix(best.Name, prefix(v.Directory))
	if best.Manifest != wantVersion {
		return refuse("context_version_mismatch")
	}
	return result{"accept", best.Name, best.Commit, wantVersion, false}
}

// walkJSON rejects duplicate decoded keys, including escaped-key duplicates.
func walkJSON(d *json.Decoder, depth int) error {
	if depth > 32 {
		return errors.New("invalid corpus")
	}
	t, err := d.Token()
	if err != nil {
		return err
	}
	switch t {
	case json.Delim('{'):
		seen := map[string]bool{}
		for d.More() {
			k, err := d.Token()
			if err != nil {
				return err
			}
			s, ok := k.(string)
			if !ok || seen[s] {
				return errors.New("invalid corpus")
			}
			seen[s] = true
			if err := walkJSON(d, depth+1); err != nil {
				return err
			}
		}
		end, err := d.Token()
		if err != nil || end != json.Delim('}') {
			return errors.New("invalid corpus")
		}
	case json.Delim('['):
		for d.More() {
			if err := walkJSON(d, depth+1); err != nil {
				return err
			}
		}
		end, err := d.Token()
		if err != nil || end != json.Delim(']') {
			return errors.New("invalid corpus")
		}
	case json.Delim('}'), json.Delim(']'):
		return errors.New("invalid corpus")
	}
	return nil
}

func decode(raw []byte) ([]vector, error) {
	bad := errors.New("invalid corpus")
	if !utf8.Valid(raw) || len(raw) > 1<<20 {
		return nil, bad
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	if err := walkJSON(d, 0); err != nil {
		return nil, bad
	}
	if _, err := d.Token(); err != io.EOF {
		return nil, bad
	}
	if !metadataShape(raw) {
		return nil, bad
	}
	var vs []vector
	d = json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if d.Decode(&vs) != nil || len(vs) == 0 {
		return nil, bad
	}
	seen := map[string]bool{}
	for _, v := range vs {
		if !idRE.MatchString(v.ID) || seen[v.ID] || v.Claim == "" ||
			(v.Phase != "resolve" && v.Phase != "replay") ||
			(v.Range != "*" && v.Range != ">=0.1.17 <1.0.0") || v.Tags == nil ||
			(v.Phase == "replay") != (v.Lock != nil) ||
			(v.Phase == "resolve" && v.ObservedCommit != "") ||
			(v.ObservedCommit != "" && !commitRE.MatchString(v.ObservedCommit)) {
			return nil, bad
		}
		if !validWant(v.Want) {
			return nil, bad
		}
		names := map[string]bool{}
		for _, t := range v.Tags {
			if names[t.Name] {
				return nil, bad
			}
			names[t.Name] = true
		}
		seen[v.ID] = true
	}
	return vs, nil
}

// Shape checks also reject missing and null primitive fields: typed Go JSON
// decoding alone would turn them into plausible zero values.
func metadataShape(raw []byte) bool {
	var rows []map[string]any
	if json.Unmarshal(raw, &rows) != nil {
		return false
	}
	stringsOK := func(m map[string]any, keys ...string) bool {
		for _, k := range keys {
			if _, ok := m[k].(string); !ok {
				return false
			}
		}
		return true
	}
	for _, r := range rows {
		if len(r) != 10 || !stringsOK(r, "id", "claim", "phase", "directory", "range", "observed_commit") {
			return false
		}
		if _, ok := r["strict"].(bool); !ok {
			return false
		}
		ts, ok := r["tags"].([]any)
		if !ok {
			return false
		}
		for _, t := range ts {
			m, ok := t.(map[string]any)
			if !ok || len(m) != 3 || !stringsOK(m, "name", "commit", "manifest_version") {
				return false
			}
		}
		if p, exists := r["lock"]; !exists {
			return false
		} else if p != nil {
			m, ok := p.(map[string]any)
			if !ok || len(m) != 4 || !stringsOK(m, "directory", "tag", "commit", "version") {
				return false
			}
		}
		want, ok := r["want"].(map[string]any)
		if !ok || len(want) != 5 || !stringsOK(want, "reason", "tag", "commit", "version") {
			return false
		}
		if _, ok := want["warning"].(bool); !ok {
			return false
		}
	}
	return true
}

func validWant(r result) bool {
	if r.Reason == "accept" {
		_, ok := stable(r.Version)
		return safeTag(r.Tag) && commitRE.MatchString(r.Commit) && ok
	}
	switch r.Reason {
	case "profile_source_invalid", "context_range_conflict", "context_version_mismatch", "strict_tag_refused", "lock_invalid", "object_invalid":
		return r.Tag == "" && r.Commit == "" && r.Version == "" && !r.Warning
	}
	return false
}

func run(vs []vector, out io.Writer) (checked, failed int) {
	for _, v := range vs {
		checked++
		if evaluate(v) != v.Want {
			failed++
			fmt.Fprintf(out, "mismatch %s\n", v.ID)
		}
	}
	return checked, failed
}

func main() {
	root := flag.String("root", ".", "specification checkout")
	flag.Parse()
	raw, err := os.ReadFile(filepath.Join(*root, "conformance", "package-overlay-tags-proposal", "cases.json"))
	if err != nil {
		fmt.Fprintln(os.Stderr, "corpus unavailable")
		os.Exit(1)
	}
	vs, err := decode(raw)
	if err != nil {
		fmt.Fprintln(os.Stderr, "invalid corpus")
		os.Exit(1)
	}
	n, bad := run(vs, os.Stdout)
	fmt.Printf("proposal cases=%d mismatches=%d runtime_cases=0\n", n, bad)
	if bad != 0 {
		os.Exit(1)
	}
}
