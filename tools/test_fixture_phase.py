"""Targeted phase-close controls; local fault injection is not Windows runtime."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

import test_fixture_lifetime as lifetime
from fixture_environment import isolated_environment
from test_fixture_environment import tree_snapshot


class FixturePhaseTests(unittest.TestCase):
    setUpClass = classmethod(lifetime.FixtureLifetimeTests.setUpClass.__func__)
    setUp = lifetime.FixtureLifetimeTests.setUp
    run_binary = lifetime.FixtureLifetimeTests.run_binary
    child_phase_args = lifetime.FixtureLifetimeTests.child_phase_args

    # Scripted reader errors exercise the real observer's identity/terminal
    # classification. They do not qualify native Windows sockets or job cleanup.
    def test_observer_terminal_classification(self):
        child = self.run_binary(["-test.run=^TestFixturePhaseObservation$"])
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

    # An actual abrupt selected body supplies status7; an abortive loopback
    # close after its genuine identity must not replace that status with2.
    def test_abrupt_reset_preserves_provider_status(self):
        self.check_reset("valid", 7, None)

    # Even after verified reset, only valid completion plus matching actual
    # provider exit can finish the owner; absent/invalid/stalled records fail2.
    def test_reset_requires_authoritative_completion(self):
        for fault, diagnostic in (("missing", "premature provider EOF"),
                                  ("invalid", "invalid completion record"),
                                  ("mismatch", "provider status mismatch"),
                                  ("stall", "child cleanup timeout")):
            with self.subTest(fault=fault):
                self.check_reset(fault, 2, diagnostic)

    # The direct-child probe's discard-only drain treats a reset as peer close,
    # while unrelated read errors still surface. These are injected reader faults.
    def test_direct_probe_drain_only_accepts_reset(self):
        for failure, accepted in ((ConnectionResetError(10054, "injected WSA reset"), True),
                                  (OSError("unrelated injected read error"), False)):
            with self.subTest(accepted=accepted):
                consumed = threading.Event()
                errors = []

                class Connection:
                    def __enter__(self): return self
                    def __exit__(self, *_): pass
                    def settimeout(self, *_): pass
                    def recv(self, *_):
                        consumed.set()
                        raise failure

                class Listener(Connection):
                    def bind(self, *_): pass
                    def listen(self): pass
                    def getsockname(self): return ("127.0.0.1", 1)
                    def accept(self): return Connection(), None

                with patch.object(lifetime.socket, "socket", return_value=Listener()), \
                     patch.object(threading, "excepthook", side_effect=lambda args: errors.append(args.exc_value)):
                    with self.child_phase_args(["--curator-fixture-child", str(self.case)]):
                        self.assertTrue(consumed.wait(2), "drain control never reached its read")
                self.assertEqual(errors, [] if accepted else [failure],
                                 "probe drain misclassified the injected terminal error")

    def check_reset(self, fault, expected, diagnostic):
        case = self.case / fault
        case.mkdir()
        outside = case / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("outside must remain identical")
        before = tree_snapshot(outside)
        shim = case / "shim"
        shim.mkdir()
        (shim / "sitecustomize.py").write_text(r'''
import builtins,json,os,pathlib,socket,struct,sys,threading,time
if pathlib.Path(sys.argv[0]).name=='fixture_environment.py' and '--go-test' in sys.argv:
    case=pathlib.Path(os.environ['PHASE_CASE'])
    child_closed=threading.Event();completion_seen=threading.Event();reset_done=threading.Event()
    def publish(name,data):
        path=case/name;pending=path.with_name(path.name+'.pending')
        pending.write_text(json.dumps(data));pending.replace(path)
    destination=sys.argv[6]
    relay=socket.socket();relay.bind(('127.0.0.1',0));relay.listen();relay.settimeout(5)
    sys.argv[6]='127.0.0.1:'+str(relay.getsockname()[1])
    host,port=destination.rsplit(':',1)
    upstream=socket.create_connection((host,int(port)),timeout=5)
    def forward():
        downstream,_=relay.accept()
        with downstream,upstream,relay:
            downstream.settimeout(5);packet=b''
            while not packet.endswith(b'\n') and len(packet)<1024:
                data=downstream.recv(1024)
                if not data: raise RuntimeError('identity plant was not applied')
                packet+=data
            identity=json.loads(packet)
            publish('identity.json',identity)
            upstream.sendall(packet)
            try:
                while True:
                    data=downstream.recv(1024)
                    if not data: break
                    upstream.sendall(data)
            except ConnectionResetError:
                pass # Actual abrupt child close on Windows may itself reset.
            child_closed.set()
            # Capture the real post-cleanup completion before provoking a
            # refusal that may terminate the provider. This is observation,
            # not a substitute completion record or a guessed child status.
            if not completion_seen.wait(5): raise RuntimeError('actual completion never reached delivery')
            upstream.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,
                                struct.pack('hh' if os.name=='nt' else 'ii',1,0))
            publish('reset.json',dict(child=identity['pid'],abortive_close=True))
            # Persist the configured fault before close can provoke the old
            # owner's termination of this provider. No post-fault marker race.
            upstream.close()
            reset_done.set()
    threading.Thread(target=forward,daemon=True).start()
    original=builtins.print
    def delivery(*args,**kwargs):
        try: record=json.loads(args[0])
        except (ValueError,TypeError,IndexError): return original(*args,**kwargs)
        if record.get('event')=='started':
            root=pathlib.Path(sys.argv[2])
            publish('provider.json',dict(pid=os.getpid(),child=record['pid'],root=str(root)))
            os.link(os.environ['PHASE_OUTSIDE'],root/'outside-hardlink')
            if os.name!='nt': (root/'outside-symlink').symlink_to(pathlib.Path(os.environ['PHASE_OUTSIDE']).parent,target_is_directory=True)
        if record.get('event')=='completed':
            if not child_closed.wait(5): raise RuntimeError('actual child phase did not close')
            publish('completed.json',record)
            completion_seen.set()
            if not reset_done.wait(5): raise RuntimeError('abortive close plant was not applied')
            fault=os.environ['PHASE_FAULT']
            if fault=='missing': os.close(1);return
            if fault=='invalid': return original(json.dumps(dict(event='invalid-completed',status=record['status'])),flush=True)
            if fault=='mismatch': return original(json.dumps(dict(record,status=0)),flush=True)
            if fault=='stall': time.sleep(30)
        return original(*args,**kwargs)
    builtins.print=delivery
''')
        temporary = case / "tmp"
        temporary.mkdir()
        dispatch = case / "body.json"
        with isolated_environment():
            env = dict(os.environ, TMPDIR=str(temporary), PYTHONPATH=str(shim),
                       PHASE_CASE=str(case), PHASE_FAULT=fault, PHASE_OUTSIDE=str(sentinel),
                       LEASE_DISPATCH=str(dispatch))
            start = time.monotonic()
            child = subprocess.run([str(self.binary), "-test.run=^TestLeaseAbruptExit$"],
                                   cwd=self.fixture, env=env, capture_output=True, text=True, timeout=13)
        output = child.stdout + child.stderr
        provider = json.loads((case / "provider.json").read_text())
        identity = json.loads((case / "identity.json").read_text())
        reset = json.loads((case / "reset.json").read_text())
        completed = json.loads((case / "completed.json").read_text())
        self.assertEqual(provider["child"], identity["pid"])
        self.assertEqual(reset, dict(child=identity["pid"], abortive_close=True))
        self.assertEqual(completed, dict(event="completed", status=7))
        self.assertTrue(dispatch.exists(), "real abrupt selected body was never dispatched")
        home = Path(json.loads(dispatch.read_text())["home"])
        self.assertFalse(home.exists())
        self.assertFalse(Path(provider["root"]).exists())
        self.assertEqual(tree_snapshot(outside), before)
        print(json.dumps(dict(control="phase-reset", fault=fault, status=child.returncode,
                              provider=provider["pid"], selected=identity["pid"],
                              seconds=round(time.monotonic()-start, 3), actual_completed_status=7,
                              root_removed=True, outside_equal=True)), flush=True)
        self.assertEqual(child.returncode, expected, output)
        if diagnostic:
            self.assertIn(diagnostic, output)
