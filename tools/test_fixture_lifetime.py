"""Bounded executable controls for the actual Go/Python fixture lease."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from fixture_environment import isolated_environment


class FixtureLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="fixture-lease-controls-")
        cls.root = Path(cls.scratch.name).resolve()
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.fixture = cls.root / "fixture"
        (cls.fixture / "tools").mkdir(parents=True)
        tools = Path(__file__).resolve().parent
        for name in ("fixture_environment.py", "fixture_process.py"):
            shutil.copyfile(tools / name, cls.fixture / "tools" / name)
        for source in (tools / "generate-vectors").glob("fixture_*_test.go"):
            shutil.copyfile(source, cls.fixture / source.name)
        (cls.fixture / "go.mod").write_text("module fixture.invalid/lease\n\ngo 1.23\n")
        (cls.fixture / "witness_test.go").write_text(r'''package main
import("encoding/json";"os";"os/exec";"testing";"time";"strconv")
// The driver must observe mandatory setup even when only this body is selected.
func TestLeaseWitness(t *testing.T) {
 if err:=os.WriteFile(os.Getenv("LEASE_DISPATCH"),[]byte(os.Getenv("HOME")),0600);err!=nil{t.Fatal(err)}
 if os.Getenv("LEASE_STATUS")=="fail" {t.Fatal("intentional child failure")}
}
// This ordinary child gets no ExtraFiles or private descriptor forwarding.
func TestLeaseOrphan(t *testing.T) {
 c:=exec.Command(os.Getenv("LEASE_PYTHON"),"-c",`import os,pathlib,socket,time,json
s=socket.create_connection(('127.0.0.1',int(os.environ['LEASE_PORT'])),timeout=5)
h=pathlib.Path(os.environ['HOME'])
pathlib.Path(os.environ['LEASE_READY']).write_text(json.dumps({'pid':os.getpid(),'parent':os.getppid(),'provider':int(os.environ['LEASE_PROVIDER']),'home':str(h)}))
s.sendall(b'R')
end=time.monotonic()+15
while not pathlib.Path(os.environ['LEASE_RELEASE']).exists() and time.monotonic()<end:time.sleep(.02)
if pathlib.Path(os.environ['LEASE_RELEASE']).exists():
 h.mkdir(parents=True,exist_ok=True);(h/'late-write').write_text('forbidden');pathlib.Path(os.environ['LEASE_RESULT']).write_text('survived')
s.close()`)
 c.Env=append(os.Environ(),"LEASE_PROVIDER="+strconv.Itoa(os.Getppid()))
 if err:=c.Start();err!=nil{t.Fatal(err)}
 if leave:=os.Getenv("LEASE_LEAVE_CHILD");leave!="" {
  end:=time.Now().Add(10*time.Second)
  for {if _,err:=os.Stat(os.Getenv("LEASE_READY"));err==nil{break};if time.Now().After(end){t.Fatal("child readiness timed out")};time.Sleep(10*time.Millisecond)}
  if leave=="fail"{t.Fatal("intentional child failure with ordinary descendant")};return
 }
 time.Sleep(20*time.Second)
}
// A revoked child stdin lease must fail while an actual selected body waits.
func TestLeaseWait(t *testing.T) {
 os.WriteFile(os.Getenv("LEASE_DISPATCH"),[]byte(os.Getenv("HOME")),0600)
 time.Sleep(20*time.Second)
}
// An abrupt exit also bypasses Go's cleanup of sibling t.TempDir trees.
func TestLeaseAbruptExit(t *testing.T) {
 t.TempDir()
 data,_:=json.Marshal(map[string]string{"home":os.Getenv("HOME")})
 os.WriteFile(os.Getenv("LEASE_DISPATCH"),data,0600)
 os.Exit(7)
}
''')
        cls.binary = cls.root / ("lease.test.exe" if os.name == "nt" else "lease.test")
        with isolated_environment():
            run = subprocess.run(["go", "test", "-c", "-o", str(cls.binary), "."],
                                 cwd=cls.fixture, capture_output=True, text=True, timeout=90)
        if run.returncode:
            raise AssertionError(run.stdout + run.stderr)

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(dir=self.root, prefix="case-"))
        self.dispatch = self.case / "dispatch"

    def run_binary(self, args, *, env=None, data=None, cwd=None):
        temporary = self.case / "tmp"
        temporary.mkdir(exist_ok=True)
        with patch.dict(os.environ, TMPDIR=str(temporary)), isolated_environment():
            child_env = dict(os.environ, LEASE_DISPATCH=str(self.dispatch))
            if env:
                child_env.update(env)
            result = subprocess.run([str(self.binary), *args], cwd=cwd or self.fixture,
                                    env=child_env, input=data, capture_output=True,
                                    text=True, timeout=20)
            self.assertEqual(list(temporary.glob("curator-go-fixture-*")), [], "outer root leaked")
            return result

    # Focused success/failure and abrupt exit preserve the child's status;
    # homes are live at dispatch and gone before the supervisor returns. The
    # abrupt case also leaves a Go temp-dir whose cleanup must not mask exit 7.
    def test_status_and_cleanup(self):
        for name, env, status in [("TestLeaseWitness", {}, 0),
                                  ("TestLeaseWitness", {"LEASE_STATUS": "fail"}, 1),
                                  ("TestLeaseAbruptExit", {}, 7)]:
            with self.subTest(name=name, status=status):
                child = self.run_binary(["-test.run=^" + name + "$"], env=env)
                self.assertEqual(child.returncode, status, child.stdout + child.stderr)
                body = self.dispatch.read_text()
                home = Path(json.loads(body)["home"] if body.startswith("{") else body)
                self.assertFalse(home.parent.exists(), "fixture root leaked after child exit")
                self.dispatch.unlink()

    # Empty/truncated/incomplete and authentic-but-cleaned grants refuse before
    # the selected body; the guard cannot be omitted with -test.run.
    def test_mandatory_grant_guard_before_focused_dispatch(self):
        owned = Path(tempfile.mkdtemp(dir=self.case, prefix="curator-go-fixture-"))
        with patch.dict(os.environ, TMPDIR=str(owned)), isolated_environment():
            captured = dict(os.environ)
            grant = {"version": 1, "root": str(Path(captured["HOME"]).parent),
                     "set": {k: captured[k] for k in ("HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL",
                              "GIT_CONFIG_NOSYSTEM", "TMPDIR", "TMP", "TEMP")}}
        for data in ("", '{"version":', "{}", json.dumps(grant) + "\n"):
            with self.subTest(data=data[:30]):
                child = self.run_binary(["--curator-fixture-child", str(owned),
                                         "-test.run=^TestLeaseWitness$"], data=data, env=captured)
                self.assertEqual(child.returncode, 2, child.stdout + child.stderr)
                self.assertIn("fixture boundary:", child.stderr)
                if data.startswith('{"version": 1'):
                    self.assertIn("missing or nonphysical HOME", child.stderr)
                self.assertFalse(self.dispatch.exists(), "invalid grant dispatched test body")

    # EOF after a complete live grant revokes the running child's lease. This
    # is distinct from malformed startup and must terminate within the budget.
    def test_child_lease_eof_is_failure(self):
        owned = Path(tempfile.mkdtemp(dir=self.case, prefix="curator-go-fixture-"))
        with patch.dict(os.environ, TMPDIR=str(owned)), isolated_environment():
            env = dict(os.environ, LEASE_DISPATCH=str(self.dispatch))
            grant = {"version": 1, "root": str(Path(env["HOME"]).parent),
                     "set": {k: env[k] for k in ("HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL",
                              "GIT_CONFIG_NOSYSTEM", "TMPDIR", "TMP", "TEMP")}}
            child = subprocess.Popen([str(self.binary), "--curator-fixture-child", str(owned),
                                      "-test.run=^TestLeaseWait$"], cwd=self.fixture, env=env,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
            try:
                child.stdin.write(json.dumps(grant) + "\n"); child.stdin.flush()
                deadline = time.monotonic() + 10
                while not self.dispatch.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(self.dispatch.exists(), "valid child never dispatched")
                child.stdin.close(); child.stdin = None
                output, error = child.communicate(timeout=10)
                self.assertEqual(child.returncode, 2, output + error)
                self.assertIn("child lease lost EOF", error)
            finally:
                if child.poll() is None:
                    child.kill(); child.wait(timeout=5)
                if child.stdin:
                    child.stdin.close()
                child.stdout.close(); child.stderr.close()
        self.assertFalse(Path(grant["root"]).exists())

    # A provider that exits without completion, lies about status, or hangs at
    # teardown cannot turn a focused run green. The temporary outer root cleans.
    def test_provider_eof_and_exit_status_fail_closed(self):
        source = self.fixture / "tools" / "fixture_environment.py"
        real = source.read_text()
        plants = [
            ("time.sleep(30)", "setup setup timed out"),
            ("raise SystemExit(0)", "setup EOF"),
            ("print('{',flush=True)", "setup unexpected EOF"),
            ("print(json.dumps({'event':'started','pid':os.getpid()}),flush=True)", "premature provider EOF"),
            ("print(json.dumps({'event':'started','pid':os.getpid()}),flush=True);"
             "print(json.dumps({'event':'completed','status':0}),flush=True);raise SystemExit(7)", "provider status mismatch"),
            ("print(json.dumps({'event':'started','pid':os.getpid()}),flush=True);"
             "print(json.dumps({'event':'completed','status':0}),flush=True);time.sleep(30)", "provider completion timeout")]

        try:
            for plant, diagnostic in plants:
                with self.subTest(plant=plant):
                    source.write_text("import os,json,time\n" + plant + "\n")
                    child = self.run_binary(["-test.run=^TestLeaseWitness$"])
                    self.assertEqual(child.returncode, 2, child.stdout + child.stderr)
                    self.assertFalse(self.dispatch.exists())
                    self.assertIn(diagnostic, child.stderr)
        finally:
            source.write_text(real)

    # Missing interpreter and child executable refuse setup and remove their
    # exclusive roots; these are spawn failures, not successful EOF controls.
    def test_spawn_failures_clean_owned_roots(self):
        child = self.run_binary(["-test.run=^TestLeaseWitness$"],
                                env={"PATH": str(self.case / "absent-bin")})
        self.assertEqual(child.returncode, 2, child.stdout + child.stderr)
        self.assertIn("fixture boundary: start", child.stderr)
        self.assertFalse(self.dispatch.exists())
        owned = Path(tempfile.mkdtemp(dir=self.case, prefix="curator-go-fixture-"))
        runner = self.fixture / "tools" / "fixture_environment.py"
        with isolated_environment():
            child = subprocess.run([sys.executable, str(runner), "--go-test", str(owned),
                                    str(self.case / "absent-command"), "unused"], input="",
                                   capture_output=True, text=True, timeout=10)
        self.assertEqual(child.returncode, 2, child.stdout + child.stderr)
        self.assertIn("FileNotFoundError", child.stderr)
        self.assertFalse(owned.exists())

    # Killing the exact outer parent revokes its lease. Both the test process
    # and its ordinary grandchild must die before cleanup; a late write cannot
    # recreate the root. A live socket proves descendant death, not just silence.
    def test_parent_death_kills_ordinary_descendant_and_cleans_root(self):
        self.check_death("parent")

    # Provider death is also fail-closed; the outer owner performs fallback
    # cleanup, and the owned group/job removes the ordinary descendant.
    def test_provider_death_kills_ordinary_descendant_and_cleans_root(self):
        self.check_death("provider")

    # Normal success/failure also terminates a surviving ordinary descendant
    # before deleting its home, and preserves the selected test's exit status.
    def test_child_exit_kills_remaining_descendant(self):
        self.check_death("child-success")
        self.case = Path(tempfile.mkdtemp(dir=self.root, prefix="case-fail-"))
        self.check_death("child-failure")

    def check_death(self, target):
        ready, release, result = [self.case / name for name in ("ready", "release", "result")]
        with socket.socket() as server, isolated_environment():
            server.bind(("127.0.0.1", 0)); server.listen(); server.settimeout(10)
            env = dict(os.environ, LEASE_PYTHON=sys.executable, LEASE_PORT=str(server.getsockname()[1]),
                       LEASE_READY=str(ready), LEASE_RELEASE=str(release), LEASE_RESULT=str(result))
            if target.startswith("child-"):
                env["LEASE_LEAVE_CHILD"] = "fail" if target == "child-failure" else "success"
            with (self.case / "parent.log").open("w") as log:
                parent = subprocess.Popen([str(self.binary), "-test.run=^TestLeaseOrphan$"],
                                          cwd=self.fixture, env=env, stdout=log, stderr=log)
                try:
                    with server.accept()[0] as connection:
                        connection.settimeout(10)
                        self.assertEqual(connection.recv(1), b"R")
                        record = json.loads(ready.read_text())
                        home = Path(record["home"])
                        if not target.startswith("child-"):
                            self.assertTrue(home.is_dir())
                        if target == "parent":
                            parent.kill()
                        elif target == "provider":
                            os.kill(record["provider"], signal.SIGKILL if os.name != "nt" else signal.SIGTERM)
                        status = parent.wait(timeout=10)
                        if target == "provider":
                            self.assertEqual(status, 2)
                        elif target == "parent":
                            self.assertNotEqual(status, 0)
                        else:
                            self.assertEqual(status, 1 if target == "child-failure" else 0)
                        try:
                            closed = connection.recv(1)
                        except ConnectionResetError:
                            closed = b""  # Windows may reset a killed peer's socket.
                        self.assertEqual(closed, b"", "ordinary child survived owner exit")
                        deadline = time.monotonic() + 10
                        while home.parent.parent.exists() and time.monotonic() < deadline:
                            time.sleep(.02)
                        self.assertFalse(home.parent.parent.exists(), "owned outer root leaked")
                        release.write_text("late write must be impossible")
                        self.assertFalse(result.exists())
                        self.assertFalse(home.exists())
                finally:
                    if parent.poll() is None:
                        parent.kill(); parent.wait(timeout=5)
