package main

import (
	"bytes"
	"encoding/json"
	"os"
	"os/exec"
	"strings"
	"testing"
)

func corpus(t *testing.T) []vector {
	t.Helper()
	b, err := os.ReadFile("../../conformance/package-overlay-tags-proposal/cases.json")
	if err != nil {
		t.Fatal(err)
	}
	vs, err := decode(b)
	if err != nil {
		t.Fatal(err)
	}
	return vs
}

// Proves all published bounded metadata expectations, not actual Git/runtime
// behavior. Individual fixture claims state the positive and forbidden cases.
func TestProposalCorpus(t *testing.T) {
	vs := corpus(t)
	for _, v := range vs {
		t.Run(v.ID, func(t *testing.T) {
			if got := evaluate(v); got != v.Want {
				t.Fatalf("got %+v, want %+v", got, v.Want)
			}
		})
	}
}

// Deliberately wrong expected acceptance/refusal must each be detected, while
// later cases still run. This catches a comparator that accepts every verdict
// or a runner that stops after its first red case.
func TestCheckerWrongVerdictsAndLaterCases(t *testing.T) {
	vs := corpus(t)
	good := vs[0]
	var bad vector
	for _, v := range vs {
		if v.Want.Reason == "context_range_conflict" {
			bad = v
			break
		}
	}
	if good.Want.Reason != "accept" || bad.ID == "" {
		t.Fatal("paired controls absent")
	}
	good.Want = result{Reason: "context_range_conflict"}
	bad.Want = vs[0].Want
	var out bytes.Buffer
	n, failed := run([]vector{good, bad, vs[1]}, &out)
	if n != 3 || failed != 2 || !strings.Contains(out.String(), "mismatch "+good.ID+"\n") || !strings.Contains(out.String(), "mismatch "+bad.ID+"\n") {
		t.Fatalf("control not detected or later case lost: %d/%d %q", n, failed, out.String())
	}
	if n, failed := run([]vector{vs[0], vs[1]}, &out); n != 2 || failed != 0 {
		t.Fatal("restored positives failed")
	}
}

// Corpus metadata is closed and exact: each single defect must refuse at
// decoding, and the original positive must remain decodable after every probe.
func TestCorpusMetadataControls(t *testing.T) {
	vs := corpus(t)
	valid, err := json.Marshal(vs[:1])
	if err != nil {
		t.Fatal(err)
	}
	changeField := func(key string, value any) string {
		var rows []map[string]any
		if err := json.Unmarshal(valid, &rows); err != nil {
			t.Fatal(err)
		}
		rows[0][key] = value
		b, err := json.Marshal(rows)
		if err != nil {
			t.Fatal(err)
		}
		return string(b)
	}
	controls := []struct{ name, raw string }{
		{"unknown", strings.Replace(string(valid), `"id":`, `"extra":1,"id":`, 1)},
		{"duplicate", strings.Replace(string(valid), `"id":`, `"id":"duplicate","id":`, 1)},
		{"escaped-duplicate", strings.Replace(string(valid), `"id":`, `"\u0069d":"duplicate","id":`, 1)},
		{"missing", strings.Replace(string(valid), `"strict":true,`, ``, 1)},
		{"null-bool", strings.Replace(string(valid), `"strict":true`, `"strict":null`, 1)},
		{"null-directory", strings.Replace(string(valid), `"directory":"contexts/sample"`, `"directory":null`, 1)},
		{"trailing", string(valid) + `{}`},
		{"trailing-comma", strings.Replace(string(valid), `}]`, `},]`, 1)},
		{"unsupported-range", changeField("range", "^0.1.17")},
		{"duplicate-id", "[" + string(valid[1:len(valid)-1]) + "," + string(valid[1:len(valid)-1]) + "]"},
		{"null-tags", changeField("tags", nil)},
		{"invalid-utf8", string(valid[:len(valid)-1]) + string([]byte{0xff}) + "]"},
	}
	for _, c := range controls {
		t.Run(c.name, func(t *testing.T) {
			if c.raw == string(valid) {
				t.Fatal("plant not applied")
			}
			if _, err := decode([]byte(c.raw)); err == nil || err.Error() != "invalid corpus" {
				t.Fatalf("intended corpus refusal absent: %v", err)
			}
			if _, err := decode(valid); err != nil {
				t.Fatal("restored positive refused", err)
			}
		})
	}
}

// Bounded stable version ordering is grounded in the written interval, with
// strict syntax/overflow refusals; this is not full environments §1.4 parsing.
func TestStableBoundaryControls(t *testing.T) {
	for _, s := range []string{"0.1.17", "0.2.0", "0.9.9", "1.0.0", "10.2.0"} {
		if _, ok := stable(s); !ok {
			t.Fatalf("valid stable refused %s", s)
		}
	}
	for _, s := range []string{"0.01.17", "0.2", "v0.2.0", "0.2.0-rc.1", "0.2.0+build", "9223372036854775808.0.0", " 0.2.0"} {
		if _, ok := stable(s); ok {
			t.Fatalf("nonstable/noncanonical admitted %s", s)
		}
	}
	if !greater([3]int64{0, 2, 0}, [3]int64{0, 1, 17}) || greater([3]int64{0, 1, 17}, [3]int64{0, 2, 0}) {
		t.Fatal("numeric ordering is wrong")
	}
}

// Exact reference spellings agree with Git on these valid/forbidden controls.
// Protocol's 255-byte bound is additionally stricter than Git and tested alone.
func TestRefGrammarAgainstGit(t *testing.T) {
	for _, s := range []string{"v0.2.0", "contexts/sample/v0.2.0", "contexts/café/v0.2.0", "contexts/nested/sample/v0.2.0", "contexts//sample/v0.2.0", "contexts/.sample/v0.2.0", "contexts/sample.lock/v0.2.0", "contexts/a b/v0.2.0", "contexts/a@{b/v0.2.0", "contexts/a../v0.2.0"} {
		got := exec.Command("git", "check-ref-format", "refs/tags/"+s).Run() == nil
		if safeTag(s) != got {
			t.Fatalf("model/Git mismatch on bounded control %q", s)
		}
	}
	if !safeTag(strings.Repeat("a", 255)) || safeTag(strings.Repeat("a", 256)) {
		t.Fatal("protocol byte bound not enforced")
	}
}
