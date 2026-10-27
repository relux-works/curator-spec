"""Authentic-record timing plants for the private Go/Python transport."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
import shutil

import test_fixture_lifetime as lifetime
from fixture_environment import isolated_environment
from test_fixture_environment import tree_snapshot


def recorded_process_exited(pid):
    """Read only this control's exact recorded PID, without signaling it."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        api.WaitForSingleObject.restype = wintypes.DWORD
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = api.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only
        if not handle:
            error = ctypes.get_last_error()
            if error == 87:  # ERROR_INVALID_PARAMETER: PID no longer exists
                return True
            raise ctypes.WinError(error)
        try:
            result = api.WaitForSingleObject(handle, 0)
            if result not in (0, 258):  # WAIT_OBJECT_0 / WAIT_TIMEOUT
                raise ctypes.WinError(ctypes.get_last_error())
            return result == 0
        finally:
            api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


class FixtureTransportTests(unittest.TestCase):
    setUpClass = classmethod(lifetime.FixtureLifetimeTests.setUpClass.__func__)
    setUp = lifetime.FixtureLifetimeTests.setUp
    run_binary = lifetime.FixtureLifetimeTests.run_binary
    child_phase_args = lifetime.FixtureLifetimeTests.child_phase_args

    # Readiness stops only setup's clock. Real body deadlines, including a
    # disabled timeout, survive; a genuine 2s body timeout remains effective.
    def test_actual_body_deadline_is_preserved(self):
        for timeout in ("0", "30s"):
            with self.subTest(timeout=timeout):
                start = time.monotonic()
                child = self.run_binary(["-test.run=^TestLeaseLong$", "-test.timeout=" + timeout])
                self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
                self.assertGreater(time.monotonic() - start, 11)
                self.assertFalse(Path(self.dispatch.read_text()).exists())
                print(json.dumps(dict(control="actual-body", timeout=timeout,
                                      seconds=round(time.monotonic()-start, 3),
                                      status=child.returncode, home_removed=True)), flush=True)
                self.dispatch.unlink()
        child = self.run_binary(["-test.run=^TestLeaseWait$", "-test.timeout=2s"])
        self.assertEqual(child.returncode, 2, child.stdout + child.stderr)
        self.assertIn("test timed out after 2s", child.stdout + child.stderr)
        self.assertNotIn("child setup timeout", child.stdout + child.stderr)

    # The real direct Go owner must scrub hostile inheritance before its live
    # grant permits dispatch; all decoy refs/config/objects and identities stay.
    def test_direct_owner_scrubs_hostile_environment(self):
        decoy = self.case / "decoy"
        decoy.mkdir()
        with isolated_environment():
            for args in (("init", "-q"), ("config", "maintenance.auto", "false"),
                         ("config", "fixture.sentinel", "preserved"),
                         ("-c", "user.name=Decoy", "-c", "user.email=decoy@example.invalid",
                          "commit", "-qm", "decoy", "--allow-empty")):
                subprocess.run(["git", "-C", str(decoy), *args], check=True,
                               capture_output=True, timeout=10)
        trace = decoy / "external.trace"
        trace.write_text("external sentinel")
        before = tree_snapshot(decoy)
        poison = dict(GIT_DIR=str(decoy / ".git"), GIT_WORK_TREE=str(decoy),
                      GIT_INDEX_FILE=str(decoy / ".git/index"), GIT_CONFIG_GLOBAL=str(trace),
                      GIT_FOO_BAR="unknown", GIT_ATTR_SOURCE="HEAD", GIT_INDEX_VERSION="4",
                      HOME=str(decoy), XDG_CONFIG_HOME=str(decoy), CODEX_HOME=str(decoy),
                      CLAUDE_CONFIG_DIR=str(decoy), SSH_AUTH_SOCK=str(decoy / "absent-socket"),
                      SSH_ASKPASS=str(decoy / "absent-askpass"))
        poison.update({key: str(trace) for key in
                       ("GIT_TRACE", "GIT_TRACE_SETUP", "GIT_TRACE2_EVENT")})
        child = self.run_binary(["-test.run=^TestLeaseWitness$"], env=poison)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        self.assertFalse(Path(self.dispatch.read_text()).exists())
        self.assertEqual(tree_snapshot(decoy), before)

    # Refused private roots cannot dispatch a command or change outside data.
    # Unix also exercises a root symlink; Windows uses the physical cases.
    def test_private_root_refusals_preserve_outside(self):
        roots = [self.case / "curator-go-fixture-nonempty", self.case / "wrong-prefix"]
        for root in roots:
            root.mkdir()
        (roots[0] / "sentinel").write_text("must remain identical")
        if os.name != "nt":
            target = self.case / "target"
            target.mkdir()
            alias = self.case / "curator-go-fixture-alias"
            alias.symlink_to(target, target_is_directory=True)
            roots.append(alias)
        before = tree_snapshot(self.case)
        runner = self.fixture / "tools/fixture_environment.py"
        for root in roots:
            with self.subTest(root=root.name), isolated_environment():
                child = subprocess.run([sys.executable, str(runner), "--go-test", str(root),
                                        sys.executable, "-c",
                                        "from pathlib import Path; Path('dispatch').touch()"],
                                       cwd=self.case, capture_output=True, text=True, timeout=10)
                self.assertEqual(child.returncode, 2, child.stdout + child.stderr)
                self.assertIn("Go fixture root must be an empty owned physical directory",
                              child.stderr)
                self.assertEqual(tree_snapshot(self.case), before)

    # Unmodified helper/consumer copies must reject each actual transport gap;
    # a marker and real child PASS distinguish the two lifecycle phases. Before
    # verified identity, a blocked supervisor forces explicit root retention;
    # only this control's independently observed process exits permit teardown.
    def test_stalled_before_grant_is_bounded(self):
        self.check_stall("started", 18, "child setup timeout")

    def test_stalled_after_child_is_bounded(self):
        self.check_stall("completed", 13, "child cleanup timeout")

    def check_stall(self, event, budget, diagnostic):
        outside = self.case / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("outside must remain identical")
        before = tree_snapshot(outside)
        shim = self.case / "shim"
        shim.mkdir()
        (shim / "sitecustomize.py").write_text(r'''
import builtins,json,os,pathlib,sys,time
if pathlib.Path(sys.argv[0]).name == 'fixture_environment.py' and '--go-test' in sys.argv:
    original_print=builtins.print
    started=None
    def timing_print(*args,**kwargs):
        global started
        try: record=json.loads(args[0])
        except (ValueError,TypeError,IndexError): return original_print(*args,**kwargs)
        if record.get('event')=='started':
            started=record
            root=pathlib.Path(sys.argv[2])
            os.link(os.environ['TRANSPORT_OUTSIDE'],root/'outside-hardlink')
            if os.name!='nt':
                (root/'outside-symlink').symlink_to(pathlib.Path(os.environ['TRANSPORT_OUTSIDE']).parent,target_is_directory=True)
            if os.environ['TRANSPORT_STALL']=='started':
                (root/'owned-readonly').mkdir();(root/'owned-readonly').chmod(0o500)
        if record.get('event')==os.environ['TRANSPORT_STALL']:
            if record['event']=='started': original_print(*args,**kwargs)
            pathlib.Path(os.environ['TRANSPORT_READY']).write_text(json.dumps(dict(provider=os.getpid(),child=started['pid'],root=sys.argv[2],record=record)))
            time.sleep(40)
        return original_print(*args,**kwargs)
    builtins.print=timing_print
''')
        marker = self.case / "transport-ready.json"
        temporary = self.case / "tmp"
        temporary.mkdir()
        with isolated_environment():
            env = dict(os.environ, TMPDIR=str(temporary), PYTHONPATH=str(shim),
                       TRANSPORT_STALL=event, TRANSPORT_OUTSIDE=str(sentinel),
                       TRANSPORT_READY=str(marker), LEASE_DISPATCH=str(self.dispatch))
            with (self.case / "outer.log").open("w+") as output:
                parent = subprocess.Popen([str(self.binary), "-test.run=^TestLeaseWitness$",
                                           "-test.timeout=2s"], cwd=self.fixture, env=env,
                                          stdout=output, stderr=output)
                ready = None
                retained = False
                started = time.monotonic()
                try:
                    deadline = started + 10
                    while not marker.exists() and time.monotonic() < deadline:
                        self.assertIsNone(parent.poll(), "plant never reached authentic record")
                        time.sleep(.02)
                    self.assertTrue(marker.exists(), "plant not applied")
                    ready = json.loads(marker.read_text())
                    self.assertEqual(ready["record"]["event"], event)
                    self.assertEqual(self.dispatch.exists(), event == "completed")
                    if event == "completed":
                        output.flush()
                        self.assertIn("PASS", (self.case / "outer.log").read_text())
                    try:
                        status = parent.wait(timeout=budget)
                    except subprocess.TimeoutExpired:
                        self.fail("outer remained alive after authentic " + event + " stall")
                    log = (self.case / "outer.log").read_text()
                    self.assertEqual(status, 2, log)
                    self.assertIn(diagnostic, log)
                    if event == "started":
                        self.assertIn("descendant cleanup unconfirmed; root retained", log)
                        self.assertIn("child grant", log)
                        retained = True
                        owned = Path(ready["root"])
                        self.assertEqual(owned.parent, temporary.resolve())
                        self.assertTrue(owned.name.startswith("curator-go-fixture-"))
                        self.assertFalse(owned.is_symlink())
                        self.assertTrue(owned.is_dir(), "unverified startup lost its root")
                finally:
                    hung = parent.poll() is None
                    if hung:
                        # Exact provider PID comes from this plant's readiness.
                        if ready:
                            os.kill(ready["provider"], 9 if os.name != "nt" else 15)
                        else:
                            parent.kill()
                    parent.wait(timeout=8)
                    if ready:
                        if retained:
                            # The plant recorded real Popen identity, independent
                            # of the protocol claim. Query only those two PIDs;
                            # never delete a retained root beneath a live owner.
                            deadline = time.monotonic() + 5
                            while not all(recorded_process_exited(ready[k]) for k in ("provider", "child")):
                                self.assertLess(time.monotonic(), deadline,
                                                "retained root still has a live recorded owner")
                                time.sleep(.02)
                            shutil.rmtree(ready["root"])
                        self.assertFalse(Path(ready["root"]).exists(), "owned root leaked")
                    self.assertEqual(tree_snapshot(outside), before)
                    print(json.dumps(dict(control=event, outer_pid=parent.pid,
                                          provider_pid=ready["provider"] if ready else None,
                                          child_pid=ready["child"] if ready else None,
                                          seconds=round(time.monotonic()-started, 3),
                                          observed_hang=hung, status=parent.returncode,
                                          retained_at_return=retained,
                                          dispatched=self.dispatch.exists(),
                                          outside_unchanged=True)), flush=True)
