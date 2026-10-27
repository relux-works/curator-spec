"""Owned fixture-process lifetime, shared by command mode and the Go bridge.

Only processes started here are terminated. Unix children get their own session;
Windows children enter a kill-on-close job before receiving the Go lease grant.
This is lifecycle containment for ordinary descendants, not a hostile-code sandbox.
"""
from __future__ import annotations

import ctypes
import os
import signal
import subprocess
import threading
import time
from contextlib import contextmanager


def exit_status(status):
    return 128 - status if status < 0 else status


class OwnedProcess:
    def __init__(self, command, **kwargs):
        self.job = None
        self.stopped = False
        if os.name == "nt":
            self.job = _WindowsJob()
        try:
            self.child = subprocess.Popen(command, start_new_session=os.name != "nt", **kwargs)
            if self.job:
                self.job.assign(self.child.pid)
        except BaseException:
            if hasattr(self, "child"):
                self.child.kill()
                self.child.wait(timeout=5)
            if self.job:
                self.job.close()
            raise

    def stop(self):
        if self.stopped:
            return
        self.stopped = True
        # Kill the group even if its leader already exited: an ordinary
        # grandchild may still hold files or try to recreate a removed HOME.
        if self.job:
            self.job.close()
            self.job = None
        elif os.name != "nt":
            try:
                os.killpg(self.child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif self.child.poll() is None:
            self.child.kill()
        self.child.wait(timeout=5)


@contextmanager
def termination_event():
    event = threading.Event()
    previous = {}
    for number in (signal.SIGTERM, signal.SIGINT):
        def terminate(number, _frame):
            event.exit_status = 128 + number
            event.set()
        previous[number] = signal.signal(number, terminate)
    try:
        yield event
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def watch_lease(stream, lost):
    # No byte is a valid release request. EOF, unexpected input and a broken
    # transport all revoke the lease. The reader never owns cleanup itself.
    def read():
        try:
            os.read(stream.fileno(), 1)
        finally:
            lost.set()
    threading.Thread(target=read, daemon=True).start()


def wait_owned(process, lost):
    try:
        while process.child.poll() is None:
            if lost.wait(.02):
                return getattr(lost, "exit_status", 2)
        return exit_status(process.child.returncode)
    finally:
        process.stop()


class _WindowsJob:
    """A native job kills ordinary descendants even if Python itself dies."""
    def __init__(self):
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", w.DWORD), ("minimum", ctypes.c_size_t),
                        ("maximum", ctypes.c_size_t), ("active", w.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", w.DWORD),
                        ("scheduling", w.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in
                        ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                        ("peak_job", ctypes.c_size_t)]
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.api.CreateJobObjectW.restype = w.HANDLE
        self.api.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.api.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.api.OpenProcess.restype = w.HANDLE
        self.api.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
        self.api.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, pid):
        handle = self.api.OpenProcess(0x0100 | 0x0001, False, pid)  # SET_QUOTA | TERMINATE
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.api.AssignProcessToJobObject(self.handle, handle):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self.api.CloseHandle(handle)

    def close(self):
        if self.handle:
            self.api.TerminateJobObject(self.handle, 2)
            self.api.CloseHandle(self.handle)
            self.handle = None


class WindowsStartGate:
    """Keep the command trampoline idle until its kill-on-close job is assigned.

    A named event avoids consuming or replacing the command's ordinary stdin.
    The Go child already has its private stdin grant as its startup barrier.
    """
    def __init__(self):
        import secrets
        self.api = _event_api()
        self.name = "Local\\curator-fixture-" + secrets.token_hex(16)
        self.handle = self.api.CreateEventW(None, True, False, self.name)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def release(self):
        if not self.api.SetEvent(self.handle):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        self.api.CloseHandle(self.handle)


def _event_api():
    from ctypes import wintypes as w
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateEventW.argtypes = [ctypes.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR]
    api.CreateEventW.restype = w.HANDLE
    api.OpenEventW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
    api.OpenEventW.restype = w.HANDLE
    api.SetEvent.argtypes = [w.HANDLE]
    api.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    api.WaitForSingleObject.restype = w.DWORD
    api.CloseHandle.argtypes = [w.HANDLE]
    return api


if __name__ == "__main__":
    import sys
    try:
        if os.name != "nt" or len(sys.argv) < 4 or sys.argv[1] != "--wait":
            raise ValueError("internal Windows command startup gate required")
        api = _event_api()
        handle = api.OpenEventW(0x00100000, False, sys.argv[2])  # SYNCHRONIZE
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if api.WaitForSingleObject(handle, 10000) != 0:
                raise TimeoutError("command job startup gate timed out")
        finally:
            api.CloseHandle(handle)
        os.execvp(sys.argv[3], sys.argv[3:])
    except Exception as error:
        print("fixture boundary:", type(error).__name__ + ":", error, file=sys.stderr)
        raise SystemExit(2)
