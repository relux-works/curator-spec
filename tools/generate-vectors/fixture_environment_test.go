package main

import (
	"bufio"
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"testing"
	"time"
)

const fixtureChild = "--curator-fixture-child"

// Direct runs supervise a separate test process. Only a private pipe grant can
// enter the child role; an inherited environment marker cannot bypass setup.
func TestMain(m *testing.M) { os.Exit(runIsolatedTests(m)) }

func runIsolatedTests(m *testing.M) (status int) {
	if len(os.Args) > 1 && os.Args[1] == fixtureChild {
		if len(os.Args) < 5 {
			return boundaryError("missing child root", nil)
		}
		root := os.Args[2]
		address, token := os.Args[3], os.Args[4]
		os.Args = append(os.Args[:1], os.Args[5:]...)
		return runFixtureChild(m, root, address, token)
	}
	python := "python3"
	if runtime.GOOS == "windows" {
		python = "python"
	}
	root, err := os.Getwd()
	if err != nil {
		return boundaryError("cwd", err)
	}
	for {
		if _, err := os.Stat(filepath.Join(root, "tools", "fixture_environment.py")); err == nil {
			break
		}
		parent := filepath.Dir(root)
		if parent == root {
			return boundaryError("cannot locate fixture_environment.py", nil)
		}
		root = parent
	}
	base := os.TempDir()
	// Match Python's strict explicit-root selection, including relative roots.
	for _, key := range []string{"TMPDIR", "TEMP", "TMP"} {
		if value := os.Getenv(key); value != "" {
			base = value
			break
		}
	}
	base, err = filepath.Abs(base)
	if err == nil {
		base, err = filepath.EvalSymlinks(base)
	}
	if err != nil {
		return boundaryError("temporary root", err)
	}
	owned, err := os.MkdirTemp(base, "curator-go-fixture-")
	if err != nil {
		return boundaryError("create root", err)
	}
	cleanupAllowed := true
	defer func() {
		if !cleanupAllowed {
			return // Never remove a root while its recorded owner may still run.
		}
		if err := removeFixtureRoot(owned); err != nil {
			status = boundaryError("root cleanup", err)
		}
	}()
	listener, err := net.Listen("tcp4", "127.0.0.1:0")
	if err != nil {
		return boundaryError("phase listener", err)
	}
	defer listener.Close()
	var nonce [32]byte
	if _, err = rand.Read(nonce[:]); err != nil {
		return boundaryError("phase nonce", err)
	}
	token := fmt.Sprintf("%x", nonce)
	executable, err := os.Executable()
	if err != nil {
		return boundaryError("executable", err)
	}
	args := []string{filepath.Join(root, "tools", "fixture_environment.py"), "--go-test", owned, executable, fixtureChild, owned, listener.Addr().String(), token}
	args = append(args, os.Args[1:]...)
	cmd := exec.Command(python, args...)
	// stdout is a private framed status channel. Test output still reaches the
	// outer test binary's stdout, including when go test uses test2json.
	cmd.Stderr = os.Stdout
	input, err := cmd.StdinPipe()
	if err != nil {
		return boundaryError("stdin", err)
	}
	output, err := cmd.StdoutPipe()
	if err != nil {
		input.Close()
		return boundaryError("stdout", err)
	}
	if err = cmd.Start(); err != nil {
		input.Close()
		output.Close()
		return boundaryError("start", err)
	}
	cleanupAllowed = false
	var once sync.Once
	done := make(chan struct{})
	var waitErr error
	startWait := func() { once.Do(func() { go func() { waitErr = cmd.Wait(); close(done) }() }) }
	// Wait begins only after protocol reads, so os/exec cannot close stdout early.
	defer func() {
		input.Close()
		output.Close()
		// Refusals may find Python blocked in transport rather than its event
		// loop. Kill this recorded provider; Windows closes its owned job too.
		_ = cmd.Process.Kill()
		startWait()
		select {
		case <-done:
			cleanupAllowed = true
		case <-time.After(5 * time.Second):
			status = boundaryError("provider termination timeout; root retained", nil)
		}
	}()
	decoder := json.NewDecoder(output)
	decoder.DisallowUnknownFields()
	var started struct {
		Event string `json:"event"`
		PID   int    `json:"pid"`
	}
	if err = decodeSetup(decoder, &started); err != nil {
		return boundaryError("setup", err)
	}
	if started.Event != "started" || started.PID <= 0 {
		return boundaryError("invalid startup record", nil)
	}
	completedCleanly := false
	defer func() {
		if !completedCleanly {
			stopFixtureGroup(started.PID)
		}
	}()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	phases := observeFixtureChild(ctx, listener, token, started.PID)
	provider := make(chan providerResult, 1)
	go func() { provider <- readFixtureCompletion(decoder, cmd, startWait, done, &waitErr) }()
	setup := time.NewTimer(10 * time.Second)
	defer setup.Stop()
	setupDeadline := setup.C
	var cleanup *time.Timer
	var cleanupDeadline <-chan time.Time
	defer func() {
		if cleanup != nil {
			cleanup.Stop()
		}
	}()
	ready, exited := false, false
	var result *providerResult
	for {
		select {
		case phase := <-phases:
			if phase.err != nil {
				return boundaryError("child phase", phase.err)
			}
			if phase.ready {
				ready = true
				setup.Stop()
				setupDeadline = nil
			} else {
				exited = true
				if cleanup == nil {
					cleanup = time.NewTimer(5 * time.Second)
					cleanupDeadline = cleanup.C
				}
			}
		case received := <-provider:
			if received.message != "" {
				return boundaryError(received.message, received.err)
			}
			result = &received
			// A child rejected before readiness legitimately returns 2. Normal
			// success/failure/abrupt exit must also have an actual child phase.
			if result.status == 2 && !ready {
				return 2
			}
			if cleanup == nil {
				cleanup = time.NewTimer(5 * time.Second)
				cleanupDeadline = cleanup.C
			}
		case <-setupDeadline:
			return boundaryError("child setup timeout", nil)
		case <-cleanupDeadline:
			return boundaryError("child cleanup timeout", nil)
		}
		if ready && exited && result != nil {
			completedCleanly = true
			return result.status
		}
	}
}

type providerResult struct {
	status  int
	message string
	err     error
}

// This decoder may wait for a record, but never owns the outer lifecycle clock.
// Refusal closes its pipe and kills its recorded provider before root cleanup.
func readFixtureCompletion(decoder *json.Decoder, cmd *exec.Cmd, startWait func(), done <-chan struct{}, waitErr *error) providerResult {
	var completed struct {
		Event  string `json:"event"`
		Status *int   `json:"status"`
	}
	if err := decoder.Decode(&completed); err != nil {
		return providerResult{message: "premature provider EOF", err: err}
	}
	if completed.Event != "completed" || completed.Status == nil || *completed.Status < 0 {
		return providerResult{message: "invalid completion record"}
	}
	// A terminal record must be the last record, and the provider's actual exit
	// must agree with it. Bound teardown so a broken provider cannot hang Wait.
	eof := make(chan error, 1)
	go func() {
		var extra any
		err := decoder.Decode(&extra)
		if err == nil {
			err = fmt.Errorf("extra provider record")
		}
		eof <- err
	}()
	select {
	case err := <-eof:
		if err != io.EOF {
			return providerResult{message: "provider completion", err: err}
		}
	case <-time.After(5 * time.Second):
		return providerResult{message: "provider completion timeout"}
	}
	startWait()
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		return providerResult{message: "provider wait timeout"}
	}
	if cmd.ProcessState.ExitCode() != *completed.Status {
		return providerResult{message: "provider status mismatch", err: *waitErr}
	}
	return providerResult{status: *completed.Status}
}

type fixturePhase struct {
	ready bool
	err   error
}

// The nonce and recorded PID bind readiness to this owned invocation. The child
// connects after grant validation and closes after m.Run or on abrupt exit.
// Python record delivery cannot postpone these independent phase observations.
func observeFixtureChild(ctx context.Context, listener net.Listener, token string, pid int) <-chan fixturePhase {
	events := make(chan fixturePhase, 2)
	go func() {
		conn, err := listener.Accept()
		if err != nil {
			events <- fixturePhase{err: err}
			return
		}
		defer conn.Close()
		stop := context.AfterFunc(ctx, func() { conn.Close() })
		defer stop()
		decoder := json.NewDecoder(io.LimitReader(conn, 1024))
		decoder.DisallowUnknownFields()
		var identity struct {
			PID   int    `json:"pid"`
			Token string `json:"token"`
		}
		if err = decoder.Decode(&identity); err != nil || identity.PID != pid || identity.Token != token {
			events <- fixturePhase{err: fmt.Errorf("invalid child readiness: %v", err)}
			return
		}
		events <- fixturePhase{ready: true}
		// No body deadline here: m.Run owns the real selected test timeout,
		// including zero. Only newline framing may precede process-owned EOF.
		reader := io.MultiReader(decoder.Buffered(), conn)
		for {
			var b [1]byte
			n, err := reader.Read(b[:])
			if err == io.EOF {
				events <- fixturePhase{}
				return
			}
			if err != nil || (n > 0 && b[0] != '\n' && b[0] != '\r') {
				events <- fixturePhase{err: fmt.Errorf("invalid child phase close: %v", err)}
				return
			}
		}
	}()
	return events
}

func decodeSetup(decoder *json.Decoder, value any) error {
	done := make(chan error, 1)
	go func() { done <- decoder.Decode(value) }()
	select {
	case err := <-done:
		return err
	case <-time.After(10 * time.Second):
		return fmt.Errorf("setup timed out")
	}
}

func boundaryError(message string, err error) int {
	fmt.Fprintln(os.Stderr, "fixture boundary:", message, err)
	return 2
}

// Every selected test, including history-only runs, must receive a complete,
// live, physical environment. EOF revokes the lease even after setup succeeded.
func runFixtureChild(m *testing.M, owned, address, token string) int {
	reader := bufio.NewReader(os.Stdin)
	decoder := json.NewDecoder(reader)
	decoder.DisallowUnknownFields()
	var grant struct {
		Version int               `json:"version"`
		Root    string            `json:"root"`
		Set     map[string]string `json:"set"`
	}
	if err := decodeSetup(decoder, &grant); err != nil {
		return boundaryError("child grant", err)
	}
	if grant.Version != 1 || grant.Set == nil {
		return boundaryError("incomplete child grant", nil)
	}
	relative, err := filepath.Rel(owned, grant.Root)
	if err != nil || relative == "." || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) || filepath.IsAbs(relative) {
		return boundaryError("grant root outside owned directory", err)
	}
	for _, key := range []string{"HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL", "TMPDIR", "TMP", "TEMP"} {
		path, found := grant.Set[key]
		physical, err := filepath.EvalSymlinks(path)
		if !found || os.Getenv(key) != path || err != nil || !filepath.IsAbs(path) || filepath.Clean(physical) != filepath.Clean(path) {
			return boundaryError("missing or nonphysical "+key, err)
		}
	}
	for key, name := range map[string]string{"HOME": "home", "XDG_CONFIG_HOME": "xdg", "GIT_CONFIG_GLOBAL": "gitconfig"} {
		if grant.Set[key] != filepath.Join(grant.Root, name) {
			return boundaryError("invalid owned "+key, nil)
		}
	}
	for _, key := range []string{"HOME", "XDG_CONFIG_HOME", "TMPDIR", "TMP", "TEMP"} {
		info, err := os.Stat(grant.Set[key])
		if err != nil || !info.IsDir() {
			return boundaryError("missing directory "+key, err)
		}
	}
	config, err := os.ReadFile(grant.Set["GIT_CONFIG_GLOBAL"])
	if err != nil || len(config) != 0 || grant.Set["GIT_CONFIG_NOSYSTEM"] != "1" || os.Getenv("GIT_CONFIG_NOSYSTEM") != "1" {
		return boundaryError("invalid owned Git config", err)
	}
	for _, entry := range os.Environ() {
		key, _, _ := strings.Cut(entry, "=")
		key = strings.ToUpper(key)
		if (strings.HasPrefix(key, "GIT_") && key != "GIT_CONFIG_GLOBAL" && key != "GIT_CONFIG_NOSYSTEM") || key == "SSH_AUTH_SOCK" || key == "SSH_ASKPASS" {
			return boundaryError("inherited "+key, nil)
		}
	}
	if runtime.GOOS == "windows" && os.Getenv("USERPROFILE") != grant.Set["HOME"] {
		return boundaryError("invalid owned USERPROFILE", nil)
	}
	for _, key := range []string{"CODEX_HOME", "CLAUDE_CONFIG_DIR", "PI_CODING_AGENT_DIR", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"} {
		if _, found := os.LookupEnv(key); found {
			return boundaryError("inherited "+key, nil)
		}
	}
	// Include decoder buffering; JSON may have read the newline or later bytes.
	lease := io.MultiReader(decoder.Buffered(), reader)
	go func() {
		for {
			var b [1]byte
			n, err := lease.Read(b[:])
			if err != nil {
				os.Exit(boundaryError("child lease lost", err))
			}
			if n > 0 && b[0] != '\n' && b[0] != '\r' {
				os.Exit(boundaryError("unexpected child lease data", nil))
			}
		}
	}()
	phase, err := net.DialTimeout("tcp4", address, 5*time.Second)
	if err != nil {
		return boundaryError("child phase connect", err)
	}
	defer phase.Close()
	if err = json.NewEncoder(phase).Encode(struct {
		PID   int    `json:"pid"`
		Token string `json:"token"`
	}{os.Getpid(), token}); err != nil {
		return boundaryError("child readiness", err)
	}
	return m.Run()
}

// Setup guards run independently of this selectable positive assertion.
func TestFixtureEnvironmentBoundary(t *testing.T) {
	if _, err := os.Stat(os.Getenv("HOME")); err != nil {
		t.Fatal(err)
	}
}

// Only this exclusively created root is walked. Directory permissions may need
// repair after a Go module download; links and regular files are never chmodded.
func removeFixtureRoot(root string) error {
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if os.IsNotExist(err) {
			return nil
		}
		if err != nil {
			return err
		}
		if !entry.IsDir() {
			return nil
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		return os.Chmod(path, info.Mode()|0700)
	})
	if err != nil {
		return err
	}
	return os.RemoveAll(root)
}
