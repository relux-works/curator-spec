package main

// The Python-owned kill-on-close Windows job handles the whole child tree,
// including provider death. The outer Go process still owns root cleanup.
func stopFixtureGroup(pid int) {}
