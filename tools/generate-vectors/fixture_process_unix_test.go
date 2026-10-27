//go:build !windows

package main

import "syscall"

// Python starts exactly this child PID as an owned session/group leader.
func stopFixtureGroup(pid int) { _ = syscall.Kill(-pid, syscall.SIGKILL) }
