// Command goversionboundary is the executable probe required by section
// 4.2.1.2 of docs/compiled-build-toolchain-requirements.md.
//
// It measures, on real Go toolchains, the boundary between the two upstream
// layers that must both accept a go.mod directive value:
//
//	shape layer     golang.org/x/mod/modfile — GoVersionRE / ToolchainRE
//	semantic layer  the go command's own version representation
//	                (internal/gover.Parse, cmd/go/internal/gover.FromToolchain)
//
// and checks the two properties the Curator contract depends on:
//
//	P1 (soundness, "no widening")  every value Curator classifies as a
//	   permitted comparison is a value upstream accepts in that position, so no
//	   ecosystem-invalid value reaches cache lookup or a compiler child.
//
//	P2 (completeness outside the security partition, "no narrowing")  every
//	   value upstream accepts in that position and that Curator does not place
//	   in the `forbidden` partition is classified as a comparison, so no
//	   Go-valid, non-forbidden file is failed for a grammar reason.
//
// P1 and P2 together give C = Upstream \ F. They are stated separately because
// C = Upstream is false and cannot be repaired: upstream accepts custom
// distribution names such as `go1.99.0-custom`, which Curator deliberately
// classifies as package influence.
//
// # Measuring the semantic layer
//
// The semantic layer is *representability*: whether the go command can hold the
// value as a version at all. It is a property of the value, not of the host.
//
// An earlier revision of this probe measured it with the exit code of
// `go mod tidy`. That is wrong, and the third layer it silently folded in is
// the reason this revision exists. `go mod tidy` also applies the running
// toolchain's TooNew gate: upstream parses the `go` line, represents it, and
// only then compares it against the local version —
// cmd/go/internal/modload/modfile.go raises `*gover.TooNewError` after
// `modfile.Parse` succeeded and `gover.Compare(f.Go.Version, gover.Local()) > 0`.
// A shape-valid, representable *future* release such as `go 1.99.0` therefore
// exits non-zero on any older host while being perfectly representable, and an
// exit-code-only classifier reports it as outside Upstream and fails P1.
//
// This revision measures the semantic layer two ways and requires them to
// agree:
//
//	isolated (primary)  gover.Parse / gover.FromToolchain, compiled from the
//	                    probed toolchain's own GOROOT sources and run by that
//	                    same toolchain. No host-version gate exists in this
//	                    path, so representability is measured directly.
//
//	command (crosscheck) the real go command, with its outcome classified into
//	                    three states rather than two: accepted, too-new, and
//	                    rejected. Too-new counts as representable, and is
//	                    recognised by upstream's own TooNewError text —
//	                    "%v requires go >= %v (running go %v%v)" — where the
//	                    version the command echoes back must equal the value
//	                    under test, which is only possible if it represented it.
//
// The crosscheck is only meaningful where the shape layer accepts the value: a
// command run over a file modfile refuses to parse measures the conjunction,
// not the semantic layer, and is reported as not applicable.
//
// # The command classifier is closed
//
// Every classifier here is a *closed* map from a command outcome to one of four
// states, and the fourth one — unknown — fails the probe. An earlier revision
// left the `toolchain` classifier open: it started at accepted and let every
// unrecognised non-zero result fall through to that start value. That is not a
// theoretical hole. Under `go build ./...`, `toolchain default` and
// `toolchain go1` exit non-zero with
//
//	go: updates to go.mod needed; to update it:
//		go mod tidy
//
// on both probed toolchains — a module-tidiness outcome that says nothing at all
// about whether the name is representable — and the open classifier scored both
// as upstream acceptance. Four of twenty-six toolchain measurements were being
// laundered that way, and any future upstream rejection layer would have been
// laundered the same way, silently.
//
// Three changes close it:
//
//   - The corroborating command for the `toolchain` position is `go version`,
//     not `go build ./...`. `go version` runs `toolchain.Select` and then prints
//     a string; every way it can fail is a toolchain-selection Fatalf. `go build`
//     runs the module loader on top of that, and the module loader has failure
//     modes of its own that are not about the value under test.
//   - Recognition is a finite list of *whole diagnostic lines*, each predicted
//     before the command runs from the value under test and the constants this
//     probe fixes (see runContext, goRecognised, tcRecognised). Everything else
//     is unknown, and unknown is a probe failure rather than a verdict.
//   - A lead plus any tail is not one outcome. Cycle 6 still recognised four
//     *families* — two `HasPrefix` leads, one `Contains` substring, and
//     upstream's TooNew lead and tail with anything between them. Cycle 7 found
//     the second lead: every colon tail after `invalid GOTOOLCHAIN "v"` was
//     scored as a rejection, although Select's colon-bearing calls quote the
//     *environment* setting — `local+path` here — and never the go.mod name.
//     That branch therefore answered for outcomes nobody had measured, and it
//     answered in the direction that hides behind an isolated-rejected value.
//
// # Fail-closedness is checked, not asserted
//
// The classifier-closure section (see closure) classifies outcomes that are
// deliberately *outside* the recognised set and requires each to yield no
// verdict: real unrelated command failures, every measured outcome cross-fed
// against every other case's value, and measured diagnostics extended the way a
// future release extends a message. Each row reports whether a wrong answer
// would have hidden — a fabricated verdict that happens to agree with the
// isolated measurement compares equal and the crosscheck stays green. Both
// directions are tracked, since `accepted` hides behind an isolated-accepted
// value and `rejected` behind an isolated-rejected one.
//
// Every probe is offline. No probe or harness module has a dependency, GOPROXY
// is off, and the toolchain-directive probe uses GOTOOLCHAIN=local+path so a
// named toolchain is searched for in PATH instead of downloaded.
//
// Usage:
//
//	go run . -go /path/to/go [-go /path/to/other/go ...] [-semantic isolated|tidy-exit]
//
// -semantic tidy-exit restores the retired exit-code-only classifier. It exists
// so the regression it caused stays reproducible: under it, a future release is
// misreported as upstream-rejected and P1 fails. It is expected to exit 1.
//
// -red unrelated-command-failure restores the retired `go build ./...` command
// form for the `toolchain` position, which injects a real unrelated non-zero
// failure for two shape-valid, isolated-representable names. It is expected to
// exit 1 with an unknown command outcome.
//
// -red open-classifier restores the four retired recognition families. It is
// expected to exit 1 in the closure section, with fabricated verdicts in both
// laundering directions.
//
// Exit status 0 means every measured upstream verdict matched the contract, both
// properties held, and nothing outside the recognised set produced a verdict, on
// every probed toolchain; 1 means at least one did not; 2 means the probe could
// not run.
package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

// disposition is the Curator section 3.1 disposition a classifier class carries.
type disposition int

const (
	compared disposition = iota
	forbidden
	mismatch // classified, but the outcome is build_toolchain_metadata_mismatch
)

func (d disposition) String() string {
	switch d {
	case compared:
		return "compared"
	case forbidden:
		return "forbidden"
	default:
		return "mismatch"
	}
}

// cmdState is the classification of a real go command outcome.
//
// The distinction between cmdTooNew and cmdRejected is what the previous
// revision added: both are non-zero exits, and only the second one says
// anything about whether the value can be represented.
//
// cmdUnknown is what this revision adds, and it is not a verdict — it is the
// absence of one. A classifier without it is open: some branch has to absorb
// the outcomes it does not recognise, and whichever verdict that branch names
// becomes an unearned measurement of every failure upstream grows later.
type cmdState int

const (
	cmdUnknown  cmdState = iota // the probe does not recognise this outcome
	cmdRejected                 // upstream refused the value itself
	cmdAccepted                 // upstream used the value
	cmdTooNew                   // upstream represented the value, then the host gate fired
)

func (s cmdState) String() string {
	switch s {
	case cmdAccepted:
		return "accepted"
	case cmdTooNew:
		return "too-new"
	case cmdRejected:
		return "rejected"
	default:
		return "UNKNOWN"
	}
}

// representable reports whether this outcome shows upstream could hold the
// value as a version. A too-new outcome does: the version was parsed, compared
// against the local one, and echoed back.
//
// It is only meaningful for a recognised outcome. cmdUnknown is never fed to
// it: an unrecognised outcome fails the probe before any verdict is derived
// from it.
func (s cmdState) representable() bool { return s == cmdAccepted || s == cmdTooNew }

// probeCase is one directive value with the classification the contract assigns
// it and the upstream verdict the contract asserts about it.
type probeCase struct {
	value string
	class int         // class number in the reference's classifier table
	label string      // class label
	disp  disposition // the class disposition
	// wantUpstream is what the contract claims the Go toolchain does with this
	// value in this position. The probe measures it rather than assuming it.
	wantUpstream bool
	note         string
}

// goCases covers both sides of every boundary of the `go` directive: values the
// shape layer rejects, values both layers accept, values the shape layer accepts
// and the semantic layer cannot represent, and — added in this revision — values
// both layers accept that the *running host* cannot build.
//
// The `go` directive has no `forbidden` class, so for it P2 reduces to
// C = Upstream.
var goCases = []probeCase{
	{"1.23", 2, "release literal", compared, true, "language version"},
	{"1.23.4", 2, "release literal", compared, true, "explicit patch"},
	{"1.21.0", 2, "release literal", compared, true, "first release of a language version"},
	{"1.23rc1", 3, "prerelease literal", compared, true, "prerelease after a minor, no patch"},
	{"1.26.0", 2, "release literal", compared, true, "FUTURE RELEASE: representable; the running host's TooNew gate is not a rejection"},
	{"1.99.0", 2, "release literal", compared, true, "FUTURE RELEASE, far: same property, and the case the exit-code-only classifier got wrong"},
	{"1.99rc1", 3, "prerelease literal", compared, true, "FUTURE PRERELEASE: representable and too-new at once"},
	{"1.23.4rc1", 4, "unrepresentable", mismatch, false, "SHAPE ACCEPTS, SEMANTIC LAYER REJECTS: prerelease after an explicit patch"},
	{"1.24.0alpha1", 4, "unrepresentable", mismatch, false, "SHAPE ACCEPTS, SEMANTIC LAYER REJECTS: same boundary, alpha kind"},
	{"1.21.3beta2", 4, "unrepresentable", mismatch, false, "SHAPE ACCEPTS, SEMANTIC LAYER REJECTS: same boundary, beta kind"},
	{"1", 4, "unclassifiable", mismatch, false, "no minor component"},
	{"0.1", 4, "unclassifiable", mismatch, false, "zero major"},
	{"1.023", 4, "unclassifiable", mismatch, false, "leading zero in a component"},
	{"1.23rc", 4, "unclassifiable", mismatch, false, "prerelease letters with no number"},
	{"v1.23", 4, "unclassifiable", mismatch, false, "v prefix"},
	{"1.23/4", 4, "unclassifiable", mismatch, false, "path separator; class 4, never package influence"},
}

// tcCases covers the `toolchain` directive, whose classifier does have a
// `forbidden` partition. The semantic layer is probed with
// GOTOOLCHAIN=local+path: a name upstream can represent is searched for in PATH
// ("cannot find ... in PATH"), a name it cannot is rejected before any search
// ("invalid toolchain" / "invalid GOTOOLCHAIN").
var tcCases = []probeCase{
	{"default", 4, "default", compared, true, "asserts the default toolchain"},
	{"go1.99.0", 5, "release name", compared, true, "release name, and a future one: no host gate applies to this position"},
	{"go1.99rc1", 6, "prerelease name", compared, true, "prerelease name"},
	{"go1", 5, "release name", compared, true, "bare major; gover.Parse reads it as 1.0.0"},
	{"go1.99.0-custom", 3, "custom-distribution name", forbidden, true, "UPSTREAM ACCEPTS, CURATOR FORBIDS: this is why C = Upstream is unachievable"},
	{"go1.99.0-bigcorp", 3, "custom-distribution name", forbidden, true, "UPSTREAM ACCEPTS, CURATOR FORBIDS: second witness"},
	{"go1.23/../evil", 2, "path-bearing name", forbidden, false, "forbidden partition also covers values upstream itself rejects"},
	{"go1.", 7, "unclassifiable", mismatch, false, "shape layer accepts, semantic layer rejects"},
	{"go1.99.0rc1x", 7, "unclassifiable", mismatch, false, "shape layer accepts, version part fails gover.Parse"},
	{"go2.0.0", 7, "unclassifiable", mismatch, false, "outside ToolchainRE"},
	{"go1x", 7, "unclassifiable", mismatch, false, "outside ToolchainRE"},
	{"godefault", 7, "unclassifiable", mismatch, false, "outside ToolchainRE"},
	{"1.23.4", 7, "unclassifiable", mismatch, false, "no go prefix and not default"},
}

// tcCommand is the corroborating command for the `toolchain` position.
//
// `go version` is the narrowest command that still runs toolchain.Select: it
// selects, and then it prints a string. Its whole failure surface is Select's
// own Fatalf set, which is what makes exit 0 a measurement of acceptance rather
// than an absence of unrelated failures.
//
// The retired form is `build ./...`, which runs the module loader on top of
// Select. -red unrelated-command-failure restores it so the outcome that
// exposed the open classifier stays reproducible.
var tcCommand = []string{"version"}

// upstreamVerdict is what a probed toolchain actually did with a value.
type upstreamVerdict struct {
	shapeAccepts bool
	shapeDetail  string

	// semanticAccepts is the layer verdict the contract is defined over.
	semanticAccepts bool
	semanticSource  string // "isolated" or "tidy-exit"

	isolated      bool // gover verdict, measured out of band
	isolatedKnown bool
	cmd           cmdState
	cmdDetail     string

	// cmdOut and cmdCode are the raw measurement the classifier was given. The
	// closure section reuses them so its checks are made of text upstream really
	// emitted rather than text this probe made up.
	cmdOut  string
	cmdCode int

	// crosscheck records whether the isolated and command measurements agree.
	// It is only evaluated where the shape layer accepts the value.
	crosscheckRun bool
	crosscheckOK  bool
}

func (v upstreamVerdict) accepts() bool { return v.shapeAccepts && v.semanticAccepts }

// harness is a compiled, per-toolchain isolation of the semantic layer.
type harness struct {
	bin        string
	goverPath  string
	goverSHA   string
	tcPath     string
	tcSHA      string
	extracted  int    // bytes of FromToolchain lifted verbatim
	extractSHA string // sha256 of exactly those bytes
	goversion  map[string]bool
	toolchainn map[string]bool
}

type prober func(work, goBin string, h *harness, ctx runContext, semantic string, value string) (upstreamVerdict, error)

func main() {
	var gos multiFlag
	semantic := flag.String("semantic", "isolated", "semantic-layer classifier: isolated (contract) or tidy-exit (retired, expected to fail)")
	red := flag.String("red", "none", "regression control: none, patch-prerelease-compared, c-equals-upstream, unrelated-command-failure, or open-classifier (each expected to fail)")
	flag.Var(&gos, "go", "path to a go binary to probe; repeatable")
	flag.Parse()
	if len(gos) == 0 {
		fmt.Fprintln(os.Stderr, "probe: at least one -go is required")
		os.Exit(2)
	}
	switch *semantic {
	case "isolated", "tidy-exit":
	default:
		fmt.Fprintf(os.Stderr, "probe: unknown -semantic %q\n", *semantic)
		os.Exit(2)
	}
	if err := applyRed(*red); err != nil {
		fmt.Fprintf(os.Stderr, "probe: %v\n", err)
		os.Exit(2)
	}

	work, err := os.MkdirTemp("", "curator-goversion-probe-")
	if err != nil {
		fmt.Fprintf(os.Stderr, "probe: %v\n", err)
		os.Exit(2)
	}
	defer os.RemoveAll(work)

	fmt.Printf("semantic classifier: %s\n", *semantic)
	fmt.Printf("regression control:  %s\n", *red)
	if *semantic == "tidy-exit" {
		fmt.Println("NOTE: this is the retired cycle-4 classifier, kept only as a regression control.")
		fmt.Println("      It treats every non-zero `go mod tidy` exit as a representation failure,")
		fmt.Println("      which folds in the running host's TooNew gate. It is expected to fail P1.")
	}
	if *red != "none" {
		fmt.Println("NOTE: a superseded classification or command form is in force as a regression")
		fmt.Println("      control. This run is expected to fail.")
	}
	fmt.Printf("toolchain-position command: go %s\n", strings.Join(tcCommand, " "))

	failures := 0
	for _, goBin := range gos {
		version, err := toolchainVersion(goBin)
		if err != nil {
			fmt.Fprintf(os.Stderr, "probe: %s: %v\n", goBin, err)
			os.Exit(2)
		}
		fmt.Printf("\n== %s (%s)\n", version, goBin)

		h, err := buildHarness(work, goBin)
		if err != nil {
			fmt.Fprintf(os.Stderr, "probe: %s: harness: %v\n", goBin, err)
			os.Exit(2)
		}
		fmt.Printf("   semantic isolation harness, built by this toolchain from its own GOROOT:\n")
		fmt.Printf("     %s\n       whole file, sha256 %s\n", h.goverPath, h.goverSHA)
		fmt.Printf("     %s\n       whole file, sha256 %s\n", h.tcPath, h.tcSHA)
		fmt.Printf("       FromToolchain lifted verbatim: %d bytes, sha256 %s\n", h.extracted, h.extractSHA)

		ctx, err := newRunContext(goBin)
		if err != nil {
			fmt.Fprintf(os.Stderr, "probe: %s: %v\n", goBin, err)
			os.Exit(2)
		}
		fmt.Printf("   exact recognised forms are predicted from: %s line %d, GOTOOLCHAIN %s/%s, local %s\n",
			ctx.modFile, ctx.goLine, ctx.goMode, ctx.tcMode, ctx.localVersion)

		goFail, goM := section(work, goBin, h, ctx, *semantic, "go.mod `go` directive", goCases, probeGoDirective)
		tcFail, tcM := section(work, goBin, h, ctx, *semantic, "go.mod `toolchain` directive", tcCases, probeToolchainDirective)
		failures += goFail + tcFail
		failures += closure(work, goBin, ctx, goM, tcM)
	}

	fmt.Println("== summary")
	fmt.Printf("toolchains probed:  %d\n", len(gos))
	fmt.Printf("cases:              %d go-directive, %d toolchain-directive\n", len(goCases), len(tcCases))
	fmt.Printf("semantic classifier: %s\n", *semantic)
	fmt.Printf("failures:           %d\n", failures)
	if failures != 0 {
		os.Exit(1)
	}
}

// applyRed restores a superseded classification so the defect it caused stays
// reproducible from this binary instead of from a hand-edited copy of it. Each
// control is expected to fail, and to fail for one named reason.
func applyRed(red string) error {
	switch red {
	case "none":
		return nil

	case "patch-prerelease-compared":
		// The cycle-3 classification: a prerelease after an explicit patch was
		// treated as an ordinary prerelease literal. The semantic layer cannot
		// represent those values, so P1 fails.
		for i := range goCases {
			if goCases[i].label == "unrepresentable" {
				goCases[i].class = 3
				goCases[i].label = "prerelease literal"
				goCases[i].disp = compared
				goCases[i].wantUpstream = true
			}
		}
		return nil

	case "c-equals-upstream":
		// Forcing C = Upstream: custom distribution names stop being package
		// influence and become ordinary release names. The `toolchain` position
		// then has no upstream-admitted forbidden value left, so the security
		// partition no longer subtracts and the run fails.
		for i := range tcCases {
			if tcCases[i].label == "custom-distribution name" {
				tcCases[i].class = 5
				tcCases[i].label = "release name"
				tcCases[i].disp = compared
			}
		}
		return nil

	case "unrelated-command-failure":
		// The cycle-5 command form: `go build ./...` for the `toolchain`
		// position. It runs the module loader after toolchain.Select, and for
		// `toolchain default` and `toolchain go1` — both shape-valid and both
		// isolated-representable — the loader exits non-zero with
		// "updates to go.mod needed", which is not a statement about the value
		// under test at all.
		//
		// This is not a synthetic injection: it is the real outcome that the
		// open classifier's fall-through branch was scoring as upstream
		// acceptance. Under the closed classifier it is an unknown command
		// outcome and the run fails.
		tcCommand = []string{"build", "./..."}
		return nil

	case "open-classifier":
		// The cycle-6 recognition: four families rather than four outcomes. Two
		// of them match a lead plus any tail, one matches any line containing a
		// substring, one matches upstream's TooNew lead and tail with anything
		// between them, anywhere in the output.
		//
		// Cycle 7 found the `invalid GOTOOLCHAIN "v":` family. It is currently
		// unreachable — Select's colon-bearing calls quote the environment value,
		// which this probe fixes at local+path — and that is precisely what makes
		// it a fabrication: it answers for outcomes nobody has measured, and it
		// answers `rejected`, which is the direction that hides behind an
		// isolated-rejected value.
		openClassifier = true
		return nil
	}
	return fmt.Errorf("unknown -red %q", red)
}

// newRunContext captures the constants the exact recognised forms are built
// from. The local version is read from the probed toolchain itself, so a form is
// predicted per toolchain rather than assumed across them.
func newRunContext(goBin string) (runContext, error) {
	banner, err := toolchainVersion(goBin)
	if err != nil {
		return runContext{}, err
	}
	fields := strings.Fields(banner)
	if len(fields) < 3 || !strings.HasPrefix(fields[2], "go") {
		return runContext{}, fmt.Errorf("cannot read a local version out of %q", banner)
	}
	return runContext{
		modFile:      "go.mod",
		goLine:       3,
		goMode:       "local",
		tcMode:       "local+path",
		localVersion: strings.TrimPrefix(fields[2], "go"),
	}, nil
}

// section measures every case in one directive position, then evaluates P1 and
// P2 over the measured results.
func section(work, goBin string, h *harness, ctx runContext, semantic, title string, cases []probeCase, p prober) (int, []upstreamVerdict) {
	fmt.Printf("\n-- %s\n\n", title)
	fmt.Printf("%-18s %-6s %-9s %-9s %-9s %-6s %-34s %s\n",
		"value", "shape", "gover", "command", "semantic", "xchk", "curator class", "measured")
	fmt.Printf("%s\n", strings.Repeat("-", 122))

	failures := 0
	measured := make([]upstreamVerdict, len(cases))
	for i, c := range cases {
		v, err := p(work, goBin, h, ctx, semantic, c.value)
		if err != nil {
			fmt.Fprintf(os.Stderr, "probe: %q: %v\n", c.value, err)
			os.Exit(2)
		}
		measured[i] = v
		ok := v.accepts() == c.wantUpstream
		if !ok {
			failures++
		}
		if v.crosscheckRun && !v.crosscheckOK {
			failures++
		}
		// An outcome the classifier does not recognise is not evidence for or
		// against anything, so it fails on its own, whatever the isolated
		// measurement said and whether or not the row otherwise agrees.
		if v.cmd == cmdUnknown {
			failures++
		}
		fmt.Printf("%-18s %-6s %-9s %-9s %-9s %-6s %-34s %s\n",
			quote(c.value), yn(v.shapeAccepts), ynk(v.isolated, v.isolatedKnown), v.cmd.String(),
			yn(v.semanticAccepts), xchk(v), fmt.Sprintf("%d %s (%s)", c.class, c.label, c.disp), verdict(ok))
		if !v.accepts() || v.cmd == cmdUnknown || (v.crosscheckRun && !v.crosscheckOK) {
			fmt.Printf("%18s %s\n", "", detail(v))
		}
	}

	// P1 — every compared value is upstream-accepted.
	var p1 []string
	for i, c := range cases {
		if c.disp == compared && !measured[i].accepts() {
			p1 = append(p1, c.value)
		}
	}
	// P2 — every upstream-accepted, non-forbidden value is compared.
	var p2 []string
	for i, c := range cases {
		if measured[i].accepts() && c.disp != forbidden && c.disp != compared {
			p2 = append(p2, c.value)
		}
	}
	// The security partition is a deliberate narrowing, so it must actually
	// subtract: at least one forbidden value has to be upstream-accepted, or the
	// separate statement of P1 and P2 would be unnecessary.
	subtracts := false
	hasForbidden := false
	for i, c := range cases {
		if c.disp != forbidden {
			continue
		}
		hasForbidden = true
		if measured[i].accepts() {
			subtracts = true
		}
	}
	// Crosscheck — the isolated semantic measurement and the real command agree
	// wherever the command can speak about the semantic layer on its own.
	var xfail []string
	for i, c := range cases {
		if measured[i].crosscheckRun && !measured[i].crosscheckOK {
			xfail = append(xfail, c.value)
		}
	}
	// Closure — every command outcome fell inside the recognised set. This is a
	// precondition of the other three properties, not one of them: a verdict
	// derived from an unrecognised outcome is not a measurement.
	var unknown []string
	for i, c := range cases {
		if measured[i].cmd == cmdUnknown {
			unknown = append(unknown, c.value)
		}
	}

	fmt.Println()
	fmt.Printf("P1 no widening      (compared subset of upstream):        %s\n", property(len(p1) == 0, p1))
	fmt.Printf("P2 no narrowing     (upstream minus forbidden compared):  %s\n", property(len(p2) == 0, p2))
	fmt.Printf("   command outcomes inside the recognised closed set:     %s\n", property(len(unknown) == 0, unknown))
	fmt.Printf("   isolated gover vs real command, where shape accepts:   %s\n", property(len(xfail) == 0, xfail))
	if hasForbidden {
		fmt.Printf("   security partition subtracts from upstream:           %s\n", verdict(subtracts))
		if !subtracts {
			failures++
		}
	} else {
		fmt.Printf("   no forbidden class in this position, so P2 is C = Upstream\n")
	}
	failures += len(p1) + len(p2)
	fmt.Println()
	return failures, measured
}

// closureCase is one classifier-closure check: an outcome, the value it is
// classified against, and the state the closed classifier must produce for it.
//
// Every check here wants cmdUnknown. That is the whole point: these are the
// outcomes the recognised set does not cover, and the property under test is
// that not covering them produces no verdict.
type closureCase struct {
	position string
	origin   string // how this outcome was obtained
	what     string // what the outcome is
	value    string // the value it is classified against
	isolated bool   // what the isolated measurement says about that value
	out      string
	code     int
}

// launders reports whether a wrong answer here would have gone unnoticed. It is
// the reason cmdUnknown has to exist: when a fabricated verdict happens to agree
// with the isolated measurement, the crosscheck compares equal and the row goes
// green for a reason nobody measured.
//
// It runs in both directions. Fabricating `accepted` hides behind an
// isolated-accepted value; fabricating `rejected` hides behind an
// isolated-rejected one. Cycle 6 closed the first; cycle 7 found the second
// still open.
func (c closureCase) launders(got cmdState) bool {
	return got != cmdUnknown && got.representable() == c.isolated
}

func (c closureCase) direction() string {
	if c.isolated {
		return "A: would hide as `accepted`"
	}
	return "B: would hide as `rejected`"
}

// closure measures the two positions' classifiers against outcomes outside their
// recognised sets, and requires every one of them to produce no verdict.
//
// The checks are built three ways, and the run says which is which:
//
//	measured             an outcome upstream really produced during this run
//	measured, unrelated  a real non-zero outcome of a real command that is not
//	                     about the value under test at all
//	measured, extended   a measured recognised diagnostic with a structural
//	                     change applied to it
//
// The third kind is constructed, and it has to be. A fail-closed classifier is a
// claim about outcomes that do not exist yet — a diagnostic upstream has not
// written, a tail it has not appended. Those cannot be measured on any host, so
// the honest way to test the property is to take text upstream did emit and
// change it in exactly the way a future release would, then require that the
// change costs the outcome its verdict rather than keeping it.
func closure(work, goBin string, ctx runContext, goM, tcM []upstreamVerdict) int {
	fmt.Printf("\n-- classifier closure\n\n")

	var checks []closureCase

	// (1) Unrelated real outcomes: a real command, a real non-zero exit, and
	// nothing in it about whether the value under test is representable.
	//
	// For the `toolchain` position this is the outcome that exposed the open
	// classifier in cycle 6: `go build ./...` runs the module loader after
	// toolchain.Select, and a redundant `toolchain` line makes the loader refuse
	// in -mod=readonly.
	tcDir, err := writeModule(work, "closure-tc", tcMod("default"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "probe: closure: %v\n", err)
		os.Exit(2)
	}
	tcUnrelated, tcUnrelatedCode, err := run(tcDir, goBin, ctx.tcMode, "build", "./...")
	if err != nil {
		fmt.Fprintf(os.Stderr, "probe: closure: %v\n", err)
		os.Exit(2)
	}
	// For the `go` position, a compile error in the package: also real, also
	// non-zero, also silent about the directive.
	goDir, err := writeModule(work, "closure-go", goMod("1.23"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "probe: closure: %v\n", err)
		os.Exit(2)
	}
	if err := os.WriteFile(filepath.Join(goDir, "p.go"), []byte("package p\n\nfunc (\n"), 0o644); err != nil {
		fmt.Fprintf(os.Stderr, "probe: closure: %v\n", err)
		os.Exit(2)
	}
	goUnrelated, goUnrelatedCode, err := run(goDir, goBin, ctx.goMode, "build", "./...")
	if err != nil {
		fmt.Fprintf(os.Stderr, "probe: closure: %v\n", err)
		os.Exit(2)
	}
	if tcUnrelatedCode == 0 || goUnrelatedCode == 0 {
		fmt.Fprintf(os.Stderr, "probe: closure: an unrelated-outcome fixture exited 0, so it measures nothing\n")
		os.Exit(2)
	}

	// Both directions, per position: the same unrelated outcome, once against a
	// value the isolated measurement accepts and once against one it rejects.
	for _, v := range pickIsolated(tcM, tcCases) {
		checks = append(checks, closureCase{"toolchain", "measured, unrelated",
			"`go build ./...` module-loader refusal", v.value, v.isolated, tcUnrelated, tcUnrelatedCode})
	}
	for _, v := range pickIsolated(goM, goCases) {
		checks = append(checks, closureCase{"go", "measured, unrelated",
			"`go build ./...` package compile error", v.value, v.isolated, goUnrelated, goUnrelatedCode})
	}

	// (2) Cross-value: every measured value-bearing outcome, classified against
	// every other case's value. A recognised form echoes the value under test, so
	// none of these may survive as a verdict.
	checks = append(checks, crossFeed("toolchain", tcCases, tcM)...)
	checks = append(checks, crossFeed("go", goCases, goM)...)

	// (3) Structural extensions of measured recognised diagnostics.
	checks = append(checks, extended("toolchain", tcCases, tcM)...)
	checks = append(checks, extended("go", goCases, goM)...)

	fmt.Printf("%-10s %-20s %-46s %-9s %-9s %s\n",
		"position", "origin", "outcome", "value", "isolated", "classified")
	fmt.Printf("%s\n", strings.Repeat("-", 122))

	failures := 0
	launderedA, launderedB := 0, 0
	for _, c := range checks {
		var got cmdState
		if c.position == "toolchain" {
			got = classifyToolchainCommand(ctx, c.out, c.code, c.value)
		} else {
			got = classifyGoCommand(ctx, c.out, c.code, c.value)
		}
		note := "ok"
		if got != cmdUnknown {
			failures++
			note = "VERDICT FABRICATED: " + got.String()
			if c.launders(got) {
				if c.isolated {
					launderedA++
				} else {
					launderedB++
				}
				note += "; LAUNDERED, direction " + c.direction()
			} else {
				note += "; would surface as a crosscheck disagreement"
			}
		}
		fmt.Printf("%-10s %-20s %-46s %-9s %-9s %s\n",
			c.position, c.origin, truncate(c.what, 46), quote(c.value), yn(c.isolated), note)
		if got != cmdUnknown {
			fmt.Printf("%42s %s\n", "", firstLine(c.out, c.code))
		}
	}

	fmt.Println()
	fmt.Printf("   checks:                                                %d\n", len(checks))
	fmt.Printf("   outcomes outside the recognised set produce no verdict: %s\n", verdict(failures == 0))
	fmt.Printf("   fabrications the crosscheck could not catch, direction A (as `accepted`, on an isolated-accepted value): %d\n", launderedA)
	fmt.Printf("   fabrications the crosscheck could not catch, direction B (as `rejected`, on an isolated-rejected value): %d\n", launderedB)
	fmt.Println()
	return failures
}

// pickIsolated returns one isolated-accepted and one isolated-rejected case, so
// a check built from them covers both laundering directions.
func pickIsolated(measured []upstreamVerdict, cases []probeCase) []struct {
	value    string
	isolated bool
} {
	var out []struct {
		value    string
		isolated bool
	}
	for _, want := range []bool{true, false} {
		for i, c := range cases {
			if measured[i].isolatedKnown && measured[i].isolated == want && measured[i].shapeAccepts {
				out = append(out, struct {
					value    string
					isolated bool
				}{c.value, want})
				break
			}
		}
	}
	return out
}

// crossFeed classifies each measured value-bearing outcome against every other
// value. Value-independent outcomes are excluded and named, because for them a
// verdict is legitimate: see crossFeedable.
func crossFeed(position string, cases []probeCase, measured []upstreamVerdict) []closureCase {
	var out []closureCase
	for j := range cases {
		if !crossFeedable(measured[j]) {
			continue
		}
		for i := range cases {
			if i == j {
				continue
			}
			out = append(out, closureCase{position, "measured",
				"outcome of `" + cases[j].value + "`", cases[i].value,
				measured[i].isolated, measured[j].cmdOut, measured[j].cmdCode})
		}
	}
	return out
}

// crossFeedable reports whether an outcome is a statement about one specific
// value, so that seeing it under a different value must produce no verdict.
//
// Exit 0 is excluded: it carries no text and is acceptance for whatever value
// produced it. The missing-go-root-module abort is excluded too, and it is the
// one recognised form that names no value at all — it is a fixed internal abort.
// Recognising it under a different value is therefore not a fabrication, and the
// direction that would matter is still covered: on an isolated-accepted value it
// classifies as rejected, which disagrees with the isolated measurement and
// fails the crosscheck.
func crossFeedable(v upstreamVerdict) bool {
	return v.cmdCode != 0 && !strings.Contains(v.cmdOut, goRootModuleAbort)
}

// extended takes measured recognised diagnostics and applies the structural
// changes a future upstream release makes to a message: a tail after it, a
// wrapper in front of it. Each result keeps the value under test inside it, so
// only exactness — not the value echo — can reject them.
func extended(position string, cases []probeCase, measured []upstreamVerdict) []closureCase {
	mutations := []struct {
		name  string
		apply func(string) string
	}{
		{"tail appended", func(line string) string { return line + ": unrelated failure" }},
		{"wrapped in front", func(line string) string { return "go: warning: " + strings.TrimPrefix(line, "go: ") }},
		{"embedded in a longer line", func(line string) string { return "go: build cache: " + line + " (ignored)" }},
	}
	var out []closureCase
	for j := range cases {
		v := measured[j]
		if v.cmdCode == 0 || v.cmd == cmdUnknown {
			continue
		}
		line := recognisedLine(v.cmdOut, v.cmd, cases[j].value)
		if line == "" {
			continue
		}
		for _, m := range mutations {
			out = append(out, closureCase{position, "measured, extended",
				m.name + " on `" + cases[j].value + "`", cases[j].value, v.isolated,
				m.apply(line), v.cmdCode})
		}
	}
	return out
}

// recognisedLine finds the diagnostic line in a measured output that carries the
// value under test, so the mutation is applied to the line that did the
// recognising rather than to an arbitrary one.
func recognisedLine(out string, state cmdState, value string) string {
	if state == cmdRejected && strings.Contains(out, goRootModuleAbort) {
		return "" // names no value; a mutation of it proves nothing about echoing
	}
	for _, raw := range strings.Split(out, "\n") {
		line := strings.TrimSpace(raw)
		if line != "" && strings.Contains(line, value) {
			return line
		}
	}
	return ""
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n-1] + "…"
}

// probeGoDirective measures both upstream layers for one `go` directive value.
//
//	shape     `go mod edit -json` parses go.mod through modfile and nothing else.
//	semantic  the isolated gover harness, crosschecked against `go mod tidy`
//	          with its outcome classified into three states.
func probeGoDirective(work, goBin string, h *harness, ctx runContext, semantic, value string) (upstreamVerdict, error) {
	dir, err := writeModule(work, "go-"+value, goMod(value))
	if err != nil {
		return upstreamVerdict{}, err
	}
	shapeOut, shapeCode, err := run(dir, goBin, ctx.goMode, "mod", "edit", "-json")
	if err != nil {
		return upstreamVerdict{}, err
	}
	semOut, semCode, err := run(dir, goBin, ctx.goMode, "mod", "tidy")
	if err != nil {
		return upstreamVerdict{}, err
	}
	state := classifyGoCommand(ctx, semOut, semCode, value)

	v := upstreamVerdict{
		shapeAccepts:  shapeCode == 0,
		shapeDetail:   firstLine(shapeOut, shapeCode),
		isolated:      h.goversion[value],
		isolatedKnown: true,
		cmd:           state,
		cmdDetail:     firstLine(semOut, semCode),
		cmdOut:        semOut,
		cmdCode:       semCode,
	}
	applySemantic(&v, semantic)
	return v, nil
}

// goMod and tcMod are the two module files under test. They are written from
// here alone, so runContext.goLine and runContext.modFile describe them.
func goMod(value string) string { return fmt.Sprintf("module ex.com/p\n\ngo %s\n", value) }
func tcMod(value string) string {
	return fmt.Sprintf("module ex.com/p\n\ngo 1.23\ntoolchain %s\n", value)
}

// probeToolchainDirective measures both upstream layers for one `toolchain`
// directive value.
//
// The probe deliberately does not install any named toolchain, so
// "cannot find X in PATH" is the accepting outcome: the name was representable
// and was searched for. Rejection is upstream refusing the name itself, before
// any search.
//
// The command is `go version`, whose only failure surface is toolchain
// selection itself — see classifyToolchainCommand and tcCommand.
func probeToolchainDirective(work, goBin string, h *harness, ctx runContext, semantic, value string) (upstreamVerdict, error) {
	dir, err := writeModule(work, "tc-"+value, tcMod(value))
	if err != nil {
		return upstreamVerdict{}, err
	}
	shapeOut, shapeCode, err := run(dir, goBin, "local", "mod", "edit", "-json")
	if err != nil {
		return upstreamVerdict{}, err
	}
	semOut, semCode, err := run(dir, goBin, ctx.tcMode, tcCommand...)
	if err != nil {
		return upstreamVerdict{}, err
	}
	state := classifyToolchainCommand(ctx, semOut, semCode, value)

	v := upstreamVerdict{
		shapeAccepts:  shapeCode == 0,
		shapeDetail:   firstLine(shapeOut, shapeCode),
		isolated:      h.toolchainn[value],
		isolatedKnown: true,
		cmd:           state,
		cmdDetail:     firstLine(semOut, semCode),
		cmdOut:        semOut,
		cmdCode:       semCode,
	}
	// This position has no host-version gate, so the retired classifier and the
	// contract classifier coincide here; the isolated measurement is used either
	// way and the crosscheck is what keeps it honest.
	applySemantic(&v, "isolated")
	return v, nil
}

// applySemantic selects which measurement becomes the semantic-layer verdict and
// runs the crosscheck between the two.
func applySemantic(v *upstreamVerdict, semantic string) {
	v.semanticSource = semantic
	switch semantic {
	case "tidy-exit":
		// The retired classifier: any non-zero exit is a representation failure.
		v.semanticAccepts = v.cmd == cmdAccepted
	default:
		v.semanticAccepts = v.isolated
	}
	// The command can only speak about the semantic layer alone once the shape
	// layer has let the value through; otherwise it is measuring the conjunction.
	// An unrecognised outcome is not a verdict either, so there is nothing to
	// compare against — it is reported as its own failure instead of being
	// folded into a disagreement it did not cause.
	if v.shapeAccepts && v.isolatedKnown && v.cmd != cmdUnknown {
		v.crosscheckRun = true
		v.crosscheckOK = v.isolated == v.cmd.representable()
	}
}

// expectedOutcome is one *exact* diagnostic line upstream emits, together with
// the state observing that line establishes.
//
// A recognised outcome is a whole line, not a lead, a prefix or a substring. A
// prefix admits every tail upstream might ever append to that lead, which is an
// open-ended family rather than one outcome: the branch then answers for
// outcomes nobody has measured, and — as cycle 7 found — an unrelated future
// diagnostic sharing the lead becomes a verdict.
type expectedOutcome struct {
	line   string
	state  cmdState
	source string // where upstream renders it
}

// runContext is everything an exact form depends on besides the value under
// test: the constants this probe itself fixes, and the running toolchain's own
// version. Nothing here is read out of command output, so a form built from it
// is a prediction the command either matches exactly or does not.
type runContext struct {
	modFile      string // how base.ShortPath renders the module file from its own directory
	goLine       int    // the line the `go` directive occupies in the written go.mod
	goMode       string // GOTOOLCHAIN for the `go`-directive command
	tcMode       string // GOTOOLCHAIN for the `toolchain`-directive command
	localVersion string // gover.Local() of the probed toolchain, e.g. "1.25.1"
}

// goRecognised is the closed set of non-zero `go`-directive outcomes, rendered
// exactly as upstream emits them for this value on this host:
//
//	go: go.mod requires go >= v (running go L; GOTOOLCHAIN=local)
//	    cmd/go/internal/gover.TooNewError — upstream parsed v, compared it
//	    against the local version and echoed it back, so it represented it.
//	go.mod:3: invalid go version 'v': must match format 1.23.0
//	    x/mod/modfile — the shape layer refused it.
//	panic: go: internal error: missing go root module
//	    modfile accepted it, gover.Parse returned the zero version, cmd/go
//	    aborted on the inconsistency.
//
// The abort is the one recognised form that names no value; see crossFeedable.
func goRecognised(ctx runContext, value string) []expectedOutcome {
	return []expectedOutcome{
		{
			fmt.Sprintf("go: %s requires go >= %s (running go %s; GOTOOLCHAIN=%s)",
				ctx.modFile, value, ctx.localVersion, ctx.goMode),
			cmdTooNew,
			"cmd/go/internal/gover.TooNewError.Error",
		},
		{
			fmt.Sprintf("%s:%d: invalid go version '%s': must match format 1.23.0",
				ctx.modFile, ctx.goLine, value),
			cmdRejected,
			"x/mod/modfile rule.go errorf",
		},
		{goRootModuleAbort, cmdRejected, "cmd/go/internal/modload.mustHaveGoRoot"},
	}
}

// goRootModuleAbort is how both probed toolchains abort on a `go` directive the
// shape layer accepted and gover.Parse could not represent.
const goRootModuleAbort = "panic: go: internal error: missing go root module"

// tcRecognised is the closed set of non-zero `toolchain`-directive outcomes. It
// is the reachable base.Fatalf set of cmd/go/internal/toolchain.Select under
// GOTOOLCHAIN=local+path, restricted to the calls that quote a name derived from
// go.mod rather than the environment setting:
//
//	go: cannot find "v" in PATH         select.go — represented, then searched for
//	go: invalid toolchain "v" in go.mod select.go — refused before any search
//	go: invalid GOTOOLCHAIN "v"         select.go — the pre-search sanity check
//
// Select's other `invalid GOTOOLCHAIN %q` calls quote the *environment* value
// while interpreting it, before go.mod is read at all. Under this probe's fixed
// GOTOOLCHAIN=local+path they quote `local+path`, never the value under test,
// and the two that carry a colon-separated tail are unreachable here for the
// same reason. They are therefore deliberately absent from this set: an outcome
// carrying that lead says nothing about the name in go.mod, so it is unknown.
func tcRecognised(ctx runContext, value string) []expectedOutcome {
	q := strconv.Quote(value)
	return []expectedOutcome{
		{"go: cannot find " + q + " in PATH", cmdAccepted, "toolchain/select.go Exec"},
		{"go: invalid toolchain " + q + " in " + ctx.modFile, cmdRejected, "toolchain/select.go Select"},
		{"go: invalid GOTOOLCHAIN " + q, cmdRejected, "toolchain/select.go Select"},
	}
}

// classify maps one command outcome onto the closed recognised set, or onto
// cmdUnknown.
//
// Matching is whole-line and exact against forms predicted before the command
// ran. Two recognised forms disagreeing inside one output is not a measurement
// either, so it is unknown rather than first-wins.
func classify(rec []expectedOutcome, out string, code int) cmdState {
	if code == 0 {
		return cmdAccepted
	}
	state := cmdUnknown
	for _, raw := range strings.Split(out, "\n") {
		line := strings.TrimSpace(raw)
		if line == "" {
			continue
		}
		for _, e := range rec {
			if line != e.line {
				continue
			}
			if state != cmdUnknown && state != e.state {
				return cmdUnknown
			}
			state = e.state
		}
	}
	return state
}

// classifyGoCommand and classifyToolchainCommand are the two position
// classifiers. Each is exact; -red open-classifier adds back the retired open
// families behind them, and nothing else consults openClassifier.
func classifyGoCommand(ctx runContext, out string, code int, value string) cmdState {
	if s := classify(goRecognised(ctx, value), out, code); s != cmdUnknown {
		return s
	}
	return classifyOpen("go", out, code, value)
}

func classifyToolchainCommand(ctx runContext, out string, code int, value string) cmdState {
	if s := classify(tcRecognised(ctx, value), out, code); s != cmdUnknown {
		return s
	}
	return classifyOpen("toolchain", out, code, value)
}

// openClassifier restores the retired open matching. See applyRed.
var openClassifier bool

// classifyOpen is the recognition this revision removed, kept executable so the
// defect it caused stays reproducible from this binary rather than from a
// hand-edited copy of it.
//
// Each of these four is a *family*: a lead plus any tail, or a substring
// anywhere in the output. Cycle 7 found the second one — every colon tail after
// `invalid GOTOOLCHAIN "v"` was scored as a rejection, so an unrelated non-zero
// outcome sharing that lead would be fabricated into a verdict that happens to
// agree with the isolated measurement for any value the isolated measurement
// already rejects.
func classifyOpen(position, out string, code int, value string) cmdState {
	if !openClassifier || code == 0 {
		return cmdUnknown
	}
	q := strconv.Quote(value)
	switch position {
	case "toolchain":
		for _, raw := range strings.Split(out, "\n") {
			line, ok := goDiagnostic(raw)
			if !ok {
				continue
			}
			switch {
			case strings.HasPrefix(line, "invalid toolchain "+q+" in "):
				return cmdRejected
			case strings.HasPrefix(line, "invalid GOTOOLCHAIN "+q+":"):
				return cmdRejected
			}
		}
	case "go":
		if tooNewEchoes(out, value) {
			return cmdTooNew
		}
		if strings.Contains(out, "invalid go version '"+value+"':") {
			return cmdRejected
		}
	}
	return cmdUnknown
}

// tooNewEchoes is the retired open TooNew matcher: upstream's lead and tail with
// anything in between, found anywhere in the output.
func tooNewEchoes(out, value string) bool {
	const (
		lead = " requires go >= "
		tail = " (running go "
	)
	i := strings.Index(out, lead)
	if i < 0 {
		return false
	}
	rest := out[i+len(lead):]
	j := strings.Index(rest, tail)
	if j < 0 {
		return false
	}
	return strings.TrimSpace(rest[:j]) == value
}

// goDiagnostic strips the "go: " prefix cmd/go sets on its own diagnostics. Only
// the retired open families need it; the exact forms carry the prefix already.
func goDiagnostic(line string) (string, bool) {
	line = strings.TrimSpace(line)
	rest, ok := strings.CutPrefix(line, "go: ")
	return rest, ok
}

// buildHarness lifts the probed toolchain's own semantic layer out of its GOROOT
// and compiles it with that same toolchain, so representability is measured
// without any command-level host gate in the path.
func buildHarness(work, goBin string) (*harness, error) {
	goroot, err := goEnv(goBin, "GOROOT")
	if err != nil {
		return nil, err
	}
	goverPath := filepath.Join(goroot, "src", "internal", "gover", "gover.go")
	goverSrc, err := os.ReadFile(goverPath)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", goverPath, err)
	}
	tcPath := filepath.Join(goroot, "src", "cmd", "go", "internal", "gover", "toolchain.go")
	tcSrc, err := os.ReadFile(tcPath)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", tcPath, err)
	}
	fromToolchain, err := extractFunc(tcSrc, "FromToolchain")
	if err != nil {
		return nil, fmt.Errorf("%s: %w", tcPath, err)
	}

	root := filepath.Join(work, "harness-"+sanitize(goBin))
	pkg := filepath.Join(root, "gover")
	if err := os.MkdirAll(pkg, 0o755); err != nil {
		return nil, err
	}
	files := map[string][]byte{
		filepath.Join(root, "go.mod"):          []byte("module harness\n\ngo 1.21\n"),
		filepath.Join(pkg, "gover.go"):         goverSrc,
		filepath.Join(pkg, "fromtoolchain.go"): []byte("package gover\n\nimport \"strings\"\n\n" + string(fromToolchain) + "\n"),
		filepath.Join(root, "main.go"):         []byte(harnessMain),
	}
	for path, data := range files {
		if err := os.WriteFile(path, data, 0o644); err != nil {
			return nil, err
		}
	}

	bin := filepath.Join(root, "harness.bin")
	if out, code, err := run(root, goBin, "local", "build", "-o", bin, "."); err != nil {
		return nil, err
	} else if code != 0 {
		return nil, fmt.Errorf("building harness failed (exit %d): %s", code, strings.TrimSpace(out))
	}

	h := &harness{
		bin:        bin,
		goverPath:  goverPath,
		goverSHA:   sha256hex(goverSrc),
		tcPath:     tcPath,
		tcSHA:      sha256hex(tcSrc),
		extracted:  len(fromToolchain),
		extractSHA: sha256hex(fromToolchain),
		goversion:  map[string]bool{},
		toolchainn: map[string]bool{},
	}

	var in bytes.Buffer
	for _, c := range goCases {
		fmt.Fprintf(&in, "goversion\t%s\n", c.value)
	}
	for _, c := range tcCases {
		fmt.Fprintf(&in, "toolchainname\t%s\n", c.value)
	}
	cmd := exec.Command(bin)
	cmd.Stdin = &in
	out, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("running harness: %w", err)
	}
	for _, line := range strings.Split(strings.TrimRight(string(out), "\n"), "\n") {
		parts := strings.Split(line, "\t")
		if len(parts) != 3 {
			return nil, fmt.Errorf("harness produced %q", line)
		}
		ok := parts[2] == "true"
		switch parts[0] {
		case "goversion":
			h.goversion[parts[1]] = ok
		case "toolchainname":
			h.toolchainn[parts[1]] = ok
		default:
			return nil, fmt.Errorf("harness produced %q", line)
		}
	}
	return h, nil
}

// harnessMain is the only hand-written line of the isolation harness. Every
// decision it reports comes from the toolchain's own gover sources.
//
// The toolchain-name predicate is the contract's own composition: `default` is
// upstream's reserved name and is not a version, so it is representable without
// going through FromToolchain.
const harnessMain = `package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"harness/gover"
)

func main() {
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		mode, value, _ := strings.Cut(sc.Text(), "\t")
		var ok bool
		switch mode {
		case "goversion":
			ok = gover.IsValid(value)
		case "toolchainname":
			ok = value == "default" || gover.FromToolchain(value) != ""
		default:
			fmt.Fprintf(os.Stderr, "harness: unknown mode %q\n", mode)
			os.Exit(2)
		}
		fmt.Printf("%s\t%s\t%v\n", mode, value, ok)
	}
}
`

// extractFunc lifts one top-level function verbatim out of a Go source file, and
// refuses to lift one that would not compile in isolation. Nothing is
// transcribed by hand, so the harness cannot drift from the toolchain it claims
// to measure.
func extractFunc(src []byte, name string) ([]byte, error) {
	marker := []byte("\nfunc " + name + "(")
	i := bytes.Index(src, marker)
	if i < 0 {
		return nil, fmt.Errorf("func %s not found", name)
	}
	start := i + 1
	end := bytes.Index(src[start:], []byte("\n}\n"))
	if end < 0 {
		return nil, fmt.Errorf("func %s is unterminated", name)
	}
	body := src[start : start+end+3]
	for _, dep := range []string{"base.", "fmt.", "errors.", "context."} {
		if bytes.Contains(body, []byte(dep)) {
			return nil, fmt.Errorf("func %s references %s and is no longer self-contained", name, dep)
		}
	}
	return body, nil
}

func writeModule(work, name, gomod string) (string, error) {
	dir := filepath.Join(work, sanitize(name))
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	if err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte(gomod), 0o644); err != nil {
		return "", err
	}
	if err := os.WriteFile(filepath.Join(dir, "p.go"), []byte("package p\n"), 0o644); err != nil {
		return "", err
	}
	return dir, nil
}

// run executes one go subcommand and returns its combined output and real exit
// code. A panic in the go command surfaces as its own non-zero code, never as a
// probe error.
func run(dir, goBin, gotoolchain string, args ...string) (string, int, error) {
	cmd := exec.Command(goBin, args...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(),
		"GOTOOLCHAIN="+gotoolchain,
		"GOFLAGS=",
		"GOPROXY=off",
		"GOWORK=off",
	)
	cmd.Env = withoutGOROOT(cmd.Env)
	out, err := cmd.CombinedOutput()
	if err == nil {
		return string(out), 0, nil
	}
	var exitErr *exec.ExitError
	if errors.As(err, &exitErr) {
		return string(out), exitErr.ExitCode(), nil
	}
	return string(out), -1, err
}

// withoutGOROOT drops an inherited GOROOT, which would otherwise point every
// probed binary at one toolchain's sources and silently collapse a multi-version
// run into a single-version one.
func withoutGOROOT(env []string) []string {
	out := env[:0:0]
	for _, kv := range env {
		if strings.HasPrefix(kv, "GOROOT=") {
			continue
		}
		out = append(out, kv)
	}
	return out
}

func goEnv(goBin, name string) (string, error) {
	cmd := exec.Command(goBin, "env", name)
	cmd.Env = withoutGOROOT(append(os.Environ(), "GOTOOLCHAIN=local"))
	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("go env %s: %w", name, err)
	}
	return strings.TrimSpace(string(out)), nil
}

func toolchainVersion(goBin string) (string, error) {
	cmd := exec.Command(goBin, "version")
	cmd.Env = withoutGOROOT(append(os.Environ(), "GOTOOLCHAIN=local"))
	out, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

func sha256hex(b []byte) string {
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}

func firstLine(out string, code int) string {
	for _, line := range strings.Split(out, "\n") {
		line = strings.TrimSpace(line)
		if line != "" && line != "go: errors parsing go.mod:" {
			return fmt.Sprintf("exit %d: %s", code, line)
		}
	}
	return fmt.Sprintf("exit %d", code)
}

func detail(v upstreamVerdict) string {
	var parts []string
	if !v.shapeAccepts {
		parts = append(parts, "shape "+v.shapeDetail)
	}
	if v.cmd == cmdUnknown {
		parts = append(parts, "UNKNOWN COMMAND OUTCOME: not in the recognised closed set, so no verdict is derived from it")
	}
	parts = append(parts, fmt.Sprintf("gover %s; command %s %s", yn(v.isolated), v.cmd, v.cmdDetail))
	return strings.Join(parts, "; ")
}

func property(ok bool, offenders []string) string {
	if ok {
		return "ok"
	}
	return "VIOLATED by " + strings.Join(offenders, ", ")
}

func yn(b bool) string {
	if b {
		return "yes"
	}
	return "no"
}

func ynk(b, known bool) string {
	if !known {
		return "n/a"
	}
	return yn(b)
}

func xchk(v upstreamVerdict) string {
	if !v.crosscheckRun {
		return "n/a"
	}
	if v.crosscheckOK {
		return "ok"
	}
	return "FAIL"
}

func verdict(b bool) string {
	if b {
		return "ok"
	}
	return "MISMATCH"
}

func quote(s string) string { return "`" + s + "`" }

func sanitize(s string) string {
	var b strings.Builder
	for _, r := range s {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9':
			b.WriteRune(r)
		default:
			b.WriteByte('_')
		}
	}
	return b.String()
}

type multiFlag []string

func (m *multiFlag) String() string     { return strings.Join(*m, ",") }
func (m *multiFlag) Set(v string) error { *m = append(*m, v); return nil }
