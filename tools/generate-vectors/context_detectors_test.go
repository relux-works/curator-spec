package main

import (
	"strings"
	"testing"
)

func detectorCaseByName(t *testing.T, name string) detectorCase {
	t.Helper()
	for _, item := range detectorCases() {
		if item.name == name {
			return item
		}
	}
	t.Fatalf("no detector case %s", name)
	return detectorCase{}
}

func TestDetectorPositiveClassesReportExactSpans(t *testing.T) {
	for _, name := range []string{"secret-aws-access-key", "secret-private-key-block", "secret-bearer-token", "secret-in-mcp-args", "secret-in-mcp-url"} {
		item := detectorCaseByName(t, name)
		findings, unmatched := detectSecretMaterial(item.pin, item.files, item.waivers)
		if len(findings) != 1 || len(unmatched) != 0 {
			t.Fatalf("%s: expected exactly one finding, got %d (%d unmatched waivers)", name, len(findings), len(unmatched))
		}
		finding := findings[0]
		body := item.files[finding.File][finding.Span[0]:finding.Span[1]]
		switch finding.Pattern {
		case "aws-access-key-id":
			if !strings.HasPrefix(body, "AKIA") || len(body) != 20 {
				t.Fatalf("%s: span does not cover the key: %q", name, body)
			}
		case "private-key-block":
			if body != "-----BEGIN OPENSSH PRIVATE KEY-----" {
				t.Fatalf("%s: span does not cover the block header: %q", name, body)
			}
		case "bearer-token":
			if strings.Contains(body, " ") || len(body) < 20 {
				t.Fatalf("%s: span does not cover the token: %q", name, body)
			}
		default:
			t.Fatalf("%s: unexpected pattern %s", name, finding.Pattern)
		}
		if finding.Waived {
			t.Fatalf("%s: nothing waived", name)
		}
	}
}

func TestDetectorNegativesAndScope(t *testing.T) {
	for _, name := range []string{"placeholder-example-key", "content-hash-not-secret", "file-outside-scope-ignored", "system-module-present"} {
		item := detectorCaseByName(t, name)
		findings, _ := detectSecretMaterial(item.pin, item.files, item.waivers)
		if len(findings) != 0 {
			t.Fatalf("%s: expected no finding, got %+v", name, findings)
		}
	}
	// Narrowing: the same key outside the placeholder rule is a finding.
	item := detectorCaseByName(t, "placeholder-example-key")
	files := map[string]string{"context/00-base.md": strings.Replace(item.files["context/00-base.md"], "AKIAXXXXXXXXXXXXXXXX", "AKIAXXXXXXXXXXXXXXXY", 1)}
	if findings, _ := detectSecretMaterial(item.pin, files, nil); len(findings) != 1 {
		t.Fatalf("a body that is not one repeated character is a finding, got %+v", findings)
	}
	// Narrowing: the out-of-scope file becomes a finding once it is in scope.
	outside := detectorCaseByName(t, "file-outside-scope-ignored")
	moved := map[string]string{"context/scratch.md": outside.files["notes/scratch.txt"]}
	if findings, _ := detectSecretMaterial(outside.pin, moved, nil); len(findings) != 1 {
		t.Fatal("a file below context/ is in scope")
	}
}

func TestDetectorWaiverClearsOnlyItsSpanAtItsPin(t *testing.T) {
	item := detectorCaseByName(t, "waived-span-clears-only-itself")
	findings, unmatched := detectSecretMaterial(item.pin, item.files, item.waivers)
	if len(findings) != 2 || len(unmatched) != 0 {
		t.Fatalf("expected two findings and a matched waiver, got %d/%d", len(findings), len(unmatched))
	}
	if !findings[0].Waived || findings[1].Waived {
		t.Fatalf("exactly the waived span is cleared: %+v", findings)
	}
	payload := detectorCaseJSON(item)
	if payload["expected"].(map[string]any)["installs"] != false {
		t.Fatal("a remaining blocking finding fails installation")
	}
	// Narrowing: shifting the span by one byte matches nothing.
	shifted := []secretWaiver{{Pin: item.pin, File: item.waivers[0].File, Span: [2]int{item.waivers[0].Span[0] + 1, item.waivers[0].Span[1] + 1}, Reason: "x"}}
	findings, unmatched = detectSecretMaterial(item.pin, item.files, shifted)
	if findings[0].Waived || len(unmatched) != 1 {
		t.Fatal("a waiver names the exact byte span or matches nothing")
	}
	other := detectorCaseByName(t, "waiver-at-other-pin-does-not-apply")
	findings, unmatched = detectSecretMaterial(other.pin, other.files, other.waivers)
	if findings[0].Waived || len(unmatched) != 1 {
		t.Fatal("a waiver at another pin matches nothing")
	}
	pinned := detectorCaseJSON(detectorCaseByName(t, "pin-does-not-clear-finding"))
	if pinned["content_hash_pin"] != true || pinned["expected"].(map[string]any)["installs"] != false {
		t.Fatal("a content-hash pin does not clear the finding")
	}
}

func TestDetectorSystemModuleWarnings(t *testing.T) {
	item := detectorCaseByName(t, "system-module-present")
	warnings := systemModuleWarnings(item.files)
	if len(warnings) != 2 {
		t.Fatalf("expected two system-module warnings, got %d", len(warnings))
	}
	if warnings[0]["package"] != "companyA" || warnings[0]["path"] != "90-system.md" || warnings[1]["selector"] != nil {
		t.Fatalf("warnings must name the package, path, and selector: %v", warnings)
	}
	payload := detectorCaseJSON(item)
	if payload["expected"].(map[string]any)["installs"] != true {
		t.Fatal("the surfacing class never blocks")
	}
}
