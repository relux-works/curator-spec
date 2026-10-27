package main

import (
	"context"
	"encoding/json"
	"io"
	"net"
	"os"
	"runtime"
	"strings"
	"syscall"
	"testing"
	"time"
)

// Scripted reads classify terminal transport errors without claiming Windows
// runtime qualification. Even a reset is lifetime progress only after identity;
// it supplies neither successful completion nor an exit status.
func TestFixturePhaseObservation(t *testing.T) {
	reset := syscall.ECONNRESET
	if runtime.GOOS == "windows" {
		reset = syscall.Errno(10054) // WSAECONNRESET, the actual wsarecv failure.
	}
	wrapped := &net.OpError{Op: "read", Net: "tcp4", Err: &os.SyscallError{Syscall: "recv", Err: reset}}
	identity := func(pid int, token string) string {
		data, _ := json.Marshal(map[string]any{"pid": pid, "token": token})
		return string(data) + "\n"
	}
	valid := identity(123, "invocation-nonce")
	for _, tc := range []struct {
		name, prefix, tail string
		terminal           error
		ready, ended       bool
	}{
		{"normal-eof", valid, "", io.EOF, true, true},
		{"wrapped-reset", valid, "", wrapped, true, true},
		{"newline-with-reset", valid, "\n", wrapped, true, true},
		{"newline-with-eof", valid, "\n", io.EOF, true, true},
		{"reset-before-identity", "", "", wrapped, false, false},
		{"reset-in-identity", "{\"pid\":", "", wrapped, false, false},
		{"malformed-identity", "{broken}\n", "", io.EOF, false, false},
		{"wrong-pid", identity(456, "invocation-nonce"), "", wrapped, false, false},
		{"wrong-nonce", identity(123, "different-nonce"), "", wrapped, false, false},
		{"unknown-field", strings.TrimSpace(valid[:len(valid)-2]) + ",\"extra\":true}\n", "", io.EOF, false, false},
		{"buffered-extra", valid + "{}", "", io.EOF, true, false},
		{"extra-with-reset", valid, "x", wrapped, true, false},
		{"extra-with-eof", valid, "x", io.EOF, true, false},
		{"unrelated-error", valid, "", io.ErrUnexpectedEOF, true, false},
		{"closed-reader", valid, "", net.ErrClosed, true, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			conn := &fixtureScriptedConn{prefix: strings.NewReader(tc.prefix), tail: []byte(tc.tail), terminal: tc.terminal}
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			events := observeFixtureChild(ctx, fixtureScriptedListener{conn}, "invocation-nonce", 123)
			next := func() fixturePhase {
				select {
				case event := <-events:
					return event
				case <-time.After(2 * time.Second):
					t.Fatal("phase observer did not terminate its scripted read")
					return fixturePhase{}
				}
			}
			first := next()
			if !tc.ready {
				if first.ready || first.err == nil || !strings.Contains(first.err.Error(), "invalid child readiness") {
					t.Fatalf("invalid identity granted readiness: %+v", first)
				}
				return
			}
			if !first.ready || first.err != nil {
				t.Fatalf("valid identity rejected: %+v", first)
			}
			last := next()
			if tc.ended {
				if last.ready || last.err != nil {
					t.Fatalf("verified terminal read must report lifetime progress, not failure/status: %+v", last)
				}
			} else if last.ready || last.err == nil || !strings.Contains(last.err.Error(), "invalid child phase close") {
				t.Fatalf("invalid trailing phase accepted: %+v", last)
			}
		})
	}
}

type fixtureScriptedListener struct{ conn net.Conn }

func (l fixtureScriptedListener) Accept() (net.Conn, error) { return l.conn, nil }
func (l fixtureScriptedListener) Close() error              { return nil }
func (l fixtureScriptedListener) Addr() net.Addr            { return nil }

type fixtureScriptedConn struct {
	net.Conn
	prefix   *strings.Reader
	tail     []byte
	terminal error
}

func (c *fixtureScriptedConn) Read(p []byte) (int, error) {
	if c.prefix.Len() > 0 {
		return c.prefix.Read(p)
	}
	n := copy(p, c.tail)
	c.tail = c.tail[n:]
	return n, c.terminal
}
func (c *fixtureScriptedConn) Close() error { return nil }

// The fixture addresses/PIDs above are reader inputs, never process-kill inputs.
var _ net.Conn = (*fixtureScriptedConn)(nil)
