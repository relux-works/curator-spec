package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"testing"
)

// TestMain protects direct `go test` and compiled test binaries as well as the
// documented wrapper. Python owns the scrub inventory and temporary homes;
// its stdin lifetime keeps those homes alive without a bypass/reexec marker.
func TestMain(m *testing.M) {
	os.Exit(runIsolatedTests(m))
}

func runIsolatedTests(m *testing.M) (status int) {
	python := "python3"
	if runtime.GOOS == "windows" {
		python = "python"
	}
	// Test binaries may also be launched from the repository root.
	root, err := os.Getwd()
	if err != nil {
		fmt.Fprintln(os.Stderr, "fixture boundary cwd:", err)
		return 2
	}
	for {
		if _, err := os.Stat(filepath.Join(root, "tools", "fixture_environment.py")); err == nil {
			break
		}
		parent := filepath.Dir(root)
		if parent == root {
			fmt.Fprintln(os.Stderr, "cannot locate fixture_environment.py from test cwd")
			return 2
		}
		root = parent
	}
	cmd := exec.Command(python, filepath.Join(root, "tools", "fixture_environment.py"), "--environment-json")
	cmd.Stderr = os.Stderr
	input, err := cmd.StdinPipe()
	if err != nil {
		fmt.Fprintln(os.Stderr, "fixture boundary stdin:", err)
		return 2
	}
	output, err := cmd.StdoutPipe()
	if err != nil {
		input.Close()
		fmt.Fprintln(os.Stderr, "fixture boundary stdout:", err)
		return 2
	}
	if err := cmd.Start(); err != nil {
		input.Close()
		fmt.Fprintln(os.Stderr, "fixture boundary start:", err)
		return 2
	}
	defer func() {
		input.Close()
		output.Close()
		if err := cmd.Wait(); err != nil {
			fmt.Fprintln(os.Stderr, "fixture boundary cleanup:", err)
			status = 2
		}
	}()
	var delta struct {
		Unset []string          `json:"unset"`
		Set   map[string]string `json:"set"`
	}
	if err := json.NewDecoder(output).Decode(&delta); err != nil {
		fmt.Fprintln(os.Stderr, "fixture boundary setup:", err)
		return 2
	}
	for _, key := range delta.Unset {
		if err := os.Unsetenv(key); err != nil {
			fmt.Fprintln(os.Stderr, "fixture boundary unset:", err)
			return 2
		}
	}
	for key, value := range delta.Set {
		if err := os.Setenv(key, value); err != nil {
			fmt.Fprintln(os.Stderr, "fixture boundary set:", err)
			return 2
		}
	}
	return m.Run()
}

// Direct Go runs must receive a live, physical home before any test body.
// Git-history access itself is covered by TestAcceptedContractDigestMatchesTag.
func TestFixtureEnvironmentBoundary(t *testing.T) {
	for _, key := range []string{"HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL", "TMPDIR", "TMP", "TEMP"} {
		path := os.Getenv(key)
		physical, err := filepath.EvalSymlinks(path)
		if err != nil || !filepath.IsAbs(path) || filepath.Clean(physical) != filepath.Clean(path) {
			t.Fatalf("%s is not an existing physical absolute path: %v", key, err)
		}
	}
	for _, key := range []string{"GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_DIR", "SSH_AUTH_SOCK"} {
		if _, found := os.LookupEnv(key); found {
			t.Fatalf("inherited selector %s survived boundary", key)
		}
	}
}
