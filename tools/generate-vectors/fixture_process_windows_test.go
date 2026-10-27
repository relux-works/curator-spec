package main

import (
	"errors"
	"syscall"
)

// The Python-owned kill-on-close Windows job handles the whole child tree,
// including provider death. The outer Go process still owns root cleanup.
func stopFixtureGroup(pid int) {}

// Windows socket reads report WSAECONNRESET, not the invented POSIX errno.
func fixtureConnectionReset(err error) bool { return errors.Is(err, syscall.WSAECONNRESET) }
