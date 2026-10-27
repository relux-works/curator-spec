"""Delivery-only startup faults after authentic ordinary-tree readiness."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_fixture_lifetime as lifetime
from fixture_environment import isolated_environment
from test_fixture_environment import tree_snapshot


class FixtureStartupTests(unittest.TestCase):
    setUpClass = classmethod(lifetime.FixtureLifetimeTests.setUpClass.__func__)
    setUp = lifetime.FixtureLifetimeTests.setUp

    # Both delivery faults must revoke the real supervisor's lease before root
    # deletion: ordinary child/grandchild sockets close and cannot recreate HOME.
    def test_invalid_started_terminates_ordinary_tree(self):
        self.check_startup("invalid", "invalid startup record")

    def test_initial_eof_terminates_ordinary_tree(self):
        self.check_startup("eof", "setup EOF")

    # Other initial-record refusals compose with lease revocation, including
    # the 10s setup deadline and a foreign PID that supplies no kill authority.
    def test_initial_refusal_variants_preserve_ownership(self):
        for fault, diagnostic in (("malformed", "setup invalid character"),
                                  ("missing", "invalid startup record"),
                                  ("zero-pid", "invalid startup record"),
                                  ("foreign-pid", "child phase"),
                                  ("deadline", "setup setup timed out")):
            with self.subTest(fault=fault):
                self.check_startup(fault, diagnostic)

    # Genuine phase bytes delayed past provider EOF must not authorize killing
    # a record-shaped foreign PID. The real supervisor still owns cleanup.
    def test_provider_eof_before_identity_preserves_foreign_tree(self):
        self.check_startup("foreign-eof", "premature provider EOF")

    # Completion rejection and the independent setup clock have the same lack
    # of PID authority while actual selected-body identity remains undelivered.
    def test_preidentity_error_and_timeout_preserve_foreign_tree(self):
        for fault, diagnostic in (("foreign-error", "invalid completion record"),
                                  ("foreign-timeout", "child setup timeout")):
            with self.subTest(fault=fault):
                self.check_startup(fault, diagnostic)

    # Provider death cannot certify cleanup: retain the root with uncertainty.
    # Unix ordinary peers survive until release; Windows kill-on-close jobs
    # terminate them. This does not claim local Windows runtime qualification.
    def test_unconfirmed_early_exit_retains_live_root(self):
        self.check_startup("provider-exit", "setup EOF", retain=True)

    def check_startup(self, fault, diagnostic, *, retain=False):
        case = self.case / fault
        case.mkdir()
        outside = case / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("outside must remain identical")
        before = tree_snapshot(outside)
        before_links = sentinel.stat().st_nlink
        script = case / "tree.py"
        script.write_text(r'''
import json,os,pathlib,socket,subprocess,sys,time
kind=sys.argv[1];case=pathlib.Path(os.environ['STARTUP_CASE']);home=pathlib.Path(os.environ['HOME'])
s=socket.create_connection(('127.0.0.1',int(os.environ['STARTUP_PORT'])),timeout=5)
(case/(kind+'.json')).write_text(json.dumps(dict(pid=os.getpid(),parent=os.getppid(),home=str(home))))
s.sendall(b'R')
if kind=='child': subprocess.Popen([sys.executable,__file__,'grandchild'])
end=time.monotonic()+25
while not (case/'release').exists() and time.monotonic()<end: time.sleep(.01)
if (case/'release').exists():
    home.mkdir(parents=True,exist_ok=True);(home/('late-'+kind)).write_text('forbidden')
    (case/('survived-'+kind)).write_text('forbidden')
s.close()
''')
        shim = case / "shim"
        shim.mkdir()
        (shim / "sitecustomize.py").write_text(r'''
import builtins,json,os,pathlib,sys,threading,time
if pathlib.Path(sys.argv[0]).name=='fixture_environment.py' and '--go-test' in sys.argv:
    # File existence is this plant's readiness signal. Publish complete bytes
    # atomically so a reader never mistakes an in-progress write for a record.
    def publish(name,data):
        path=pathlib.Path(os.environ['STARTUP_CASE'],name)
        pending=path.with_name(path.name+'.pending')
        pending.write_bytes(data);pending.replace(path)
    if os.environ['STARTUP_FAULT'] in ('foreign-eof','foreign-error','foreign-timeout'):
        # Reuse the actual child identity, nonce and live connection. Only its
        # delivery is held, as in the independent authority-order witness.
        import socket
        destination=sys.argv[6]
        proxy=socket.socket();proxy.bind(('127.0.0.1',0));proxy.listen();proxy.settimeout(7)
        sys.argv[6]='127.0.0.1:'+str(proxy.getsockname()[1])
        host,port=destination.rsplit(':',1)
        upstream=socket.create_connection((host,int(port)),timeout=5)
        def hold_phase():
            downstream,_=proxy.accept()
            with downstream,upstream,proxy:
                downstream.settimeout(7)
                packet=b''
                while not packet.endswith(b'\n') and len(packet)<1024:
                    data=downstream.recv(1024)
                    if not data: raise RuntimeError('premature phase EOF in plant')
                    packet+=data
                publish('phase-held.json',packet)
                time.sleep(15 if os.environ['STARTUP_FAULT']=='foreign-timeout' else 6)
                upstream.sendall(packet)
        threading.Thread(target=hold_phase,daemon=True).start()
    original=builtins.print
    def delivery(*args,**kwargs):
        try: record=json.loads(args[0])
        except (ValueError,TypeError,IndexError): return original(*args,**kwargs)
        if record.get('event')!='started': return original(*args,**kwargs)
        case=pathlib.Path(os.environ['STARTUP_CASE']);root=pathlib.Path(sys.argv[2])
        publish('provider.json',json.dumps(dict(pid=os.getpid(),child=record['pid'],root=str(root))).encode())
        os.link(os.environ['STARTUP_OUTSIDE'],root/'outside-hardlink')
        if os.name!='nt': (root/'outside-symlink').symlink_to(pathlib.Path(os.environ['STARTUP_OUTSIDE']).parent,target_is_directory=True)
        def send():
            end=time.monotonic()+7
            while not (case/'grandchild.json').exists() and time.monotonic()<end: time.sleep(.01)
            if not (case/'grandchild.json').exists(): os._exit(9)
            fault=os.environ['STARTUP_FAULT']
            publish('plant.json',json.dumps(dict(actual=record,fault=fault)).encode())
            if fault=='eof': os.close(1)
            elif fault=='invalid': original(json.dumps(dict(record,event='invalid-started')),flush=True)
            elif fault=='malformed': original('{broken}',flush=True)
            elif fault=='missing': original('{}',flush=True)
            elif fault=='zero-pid': original(json.dumps(dict(record,pid=0)),flush=True)
            elif fault=='foreign-pid': original(json.dumps(dict(record,pid=int(os.environ['STARTUP_FOREIGN_PID']))),flush=True)
            elif fault in ('foreign-eof','foreign-error','foreign-timeout'):
                original(json.dumps(dict(record,pid=int(os.environ['STARTUP_FOREIGN_PID']))),flush=True)
                if fault=='foreign-eof': os.close(1)
                elif fault=='foreign-error': original(json.dumps(dict(event='invalid-completed')),flush=True)
            elif fault=='provider-exit': os._exit(9)
            # deadline leaves started undelivered while actual supervision runs.
        threading.Thread(target=send,daemon=True).start()
        # Return to the actual helper: it delivers its authentic grant and
        # supervises the actual selected body while only record delivery waits.
    builtins.print=delivery
''')
        temporary = case / "tmp"
        temporary.mkdir()
        peers = []
        records = {}
        parent = None
        root = None
        observed = None
        foreign = None
        started = time.monotonic()
        with socket.socket() as server, patch.dict(os.environ, TMPDIR=str(temporary)), isolated_environment():
            server.bind(("127.0.0.1", 0))
            server.listen()
            server.settimeout(10)
            env = dict(os.environ, LEASE_DISPATCH=str(case / "body.json"),
                       LEASE_PYTHON=sys.executable, LEASE_TREE_SCRIPT=str(script),
                       PYTHONPATH=str(shim), STARTUP_CASE=str(case), STARTUP_FAULT=fault,
                       STARTUP_PORT=str(server.getsockname()[1]), STARTUP_OUTSIDE=str(sentinel))
            if fault.startswith("foreign-"):
                foreign = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                           env=env, start_new_session=os.name != "nt")
                env["STARTUP_FOREIGN_PID"] = str(foreign.pid)
            with (case / "outer.log").open("w") as log:
                parent = subprocess.Popen([str(self.binary), "-test.run=^TestLeaseStartup$",
                                           "-test.timeout=25s"], cwd=self.fixture, env=env,
                                          stdout=log, stderr=log)
                try:
                    for _ in range(2):
                        peer, _ = server.accept()
                        peer.settimeout(5)
                        peers.append(peer)
                        self.assertEqual(peer.recv(1), b"R")
                    for name in ("child", "grandchild", "provider", "body", "plant"):
                        path = case / (name + ".json")
                        deadline = time.monotonic() + 8
                        while not path.exists() and time.monotonic() < deadline:
                            time.sleep(.01)
                        self.assertTrue(path.exists(), "authentic startup plant not applied: " + name)
                        records[name] = json.loads(path.read_text())
                    self.assertEqual(records["provider"]["child"], records["body"]["pid"])
                    self.assertEqual(records["child"]["parent"], records["body"]["pid"])
                    self.assertEqual(records["grandchild"]["parent"], records["child"]["pid"])
                    self.assertEqual(records["plant"]["actual"],
                                     dict(event="started", pid=records["body"]["pid"]))
                    if fault in ("foreign-eof", "foreign-error", "foreign-timeout"):
                        held = json.loads((case / "phase-held.json").read_text())
                        self.assertEqual(held["pid"], records["body"]["pid"])
                        self.assertEqual(len(held["token"]), 64)
                        self.assertNotEqual(held["pid"], foreign.pid)
                    root = Path(records["provider"]["root"])
                    self.assertEqual(root.parent, temporary.resolve())
                    self.assertTrue(root.name.startswith("curator-go-fixture-"))
                    status = parent.wait(timeout=18 if fault in ("deadline", "foreign-timeout") else 9)
                    output = (case / "outer.log").read_text()
                    self.assertEqual(status, 2, output)
                    self.assertIn(diagnostic, output)
                    alive = []
                    for peer in peers:
                        peer.settimeout(.2)
                        try:
                            alive.append(peer.recv(1) != b"")
                        except socket.timeout:
                            alive.append(True)
                        except ConnectionResetError:
                            alive.append(False)
                    observed = dict(fault=fault, outer=parent.pid,
                                    provider=records["provider"]["pid"],
                                    selected=records["body"]["pid"],
                                    child=records["child"]["pid"],
                                    grandchild=records["grandchild"]["pid"],
                                    seconds=round(time.monotonic()-started, 3), status=status,
                                    root_removed=not root.exists(), surviving_peers=alive,
                                    home_at_return=Path(records["body"]["home"]).exists())
                    if foreign:
                        observed.update(foreign_pid=foreign.pid, foreign_status=foreign.poll())
                        self.assertIsNone(foreign.poll(), "unverified PID killed outside fixture tree")
                        observed.update(foreign_pid=foreign.pid, foreign_alive=True)
                    if retain:
                        self.assertTrue(root.exists(), "unknown live tree lost its root")
                        self.assertIn("descendant cleanup unconfirmed; root retained", output)
                        self.assertEqual(alive, [os.name != "nt"] * 2,
                                         "ordinary peers must follow session/job ownership")
                    else:
                        self.assertEqual(alive, [False, False],
                                         "ordinary descendants survived early refusal/root deletion")
                        self.assertFalse(root.exists(), "completed cleanup retained root")
                finally:
                    # A failed old-byte control releases bounded ordinary
                    # witnesses to exit, without killing owners to expose it.
                    (case / "release").write_text("bounded witness release")
                    for peer in peers:
                        peer.settimeout(5)
                        try:
                            self.assertEqual(peer.recv(1), b"", "released witness did not exit")
                        except ConnectionResetError:
                            pass
                        finally:
                            peer.close()
                    if parent.poll() is None:
                        parent.kill()
                        parent.wait(timeout=5)
                    if foreign:
                        foreign.kill()
                        foreign.wait(timeout=5)
                    if observed:
                        observed.update(home_recreated=not observed["home_at_return"] and Path(records["body"]["home"]).exists(),
                                        late_markers=len(list(case.glob("survived-*"))))
                    if root and root.exists():
                        # Exact validated control root, after both peers EOF.
                        shutil.rmtree(root)
                    self.assertEqual(tree_snapshot(outside), before)
                    self.assertEqual(sentinel.stat().st_nlink, before_links)
                    if observed:
                        observed["outside_equal"] = True
                        print(json.dumps(observed), flush=True)
                        if not any(observed["surviving_peers"]):
                            self.assertFalse(observed["home_recreated"])
                            self.assertEqual(observed["late_markers"], 0)
