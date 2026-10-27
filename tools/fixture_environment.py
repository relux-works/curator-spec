"""Shared process boundary for unittest modules that drive Git fixtures.

Install with unittest.enterModuleContext(isolated_environment()) in
setUpModule, before any fixture setup. Subprocesses (including validators)
then inherit the same safe defaults without patching subprocess or Git calls.
Tests may still provide explicit environment overrides inside that boundary.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
import json
import sys
from pathlib import Path
import tempfile


def _managed(key: str) -> bool:
    key = key.upper()
    return key.startswith("GIT_") or key in {
        "SSH_AUTH_SOCK", "SSH_ASKPASS", "HOME", "XDG_CONFIG_HOME", "TMPDIR", "TMP", "TEMP",
        "CODEX_HOME", "CLAUDE_CONFIG_DIR", "PI_CODING_AGENT_DIR",
        "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME",
    } or (os.name == "nt" and key == "USERPROFILE")


def _temporary_root() -> Path:
    # tempfile caches its selection and silently falls back for invalid roots.
    # Honor explicit roots and refuse rather than selecting a different boundary.
    selected = next((os.environ[k] for k in ("TMPDIR", "TEMP", "TMP")
                     if os.environ.get(k)), None)
    if selected is None:
        selected = tempfile.gettempdir()
    root = Path(selected).resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    return root


@contextmanager
def isolated_environment():
    """Scrub inherited GIT_*/SSH keys, pin homes, then restore the caller."""
    previous = {key: value for key, value in os.environ.items() if _managed(key)}
    temporary_root = _temporary_root()
    with tempfile.TemporaryDirectory(prefix="curator-test-environment-",
                                     dir=temporary_root) as directory:
        root = Path(directory).resolve(strict=True)
        home = root / "home"
        xdg = root / "xdg"
        home.mkdir(mode=0o700)
        xdg.mkdir(mode=0o700)
        config = root / "gitconfig"
        config.touch(mode=0o600)
        try:
            for key in list(os.environ):
                if _managed(key):
                    del os.environ[key]
            # Git allowlist: use only the fixture-owned empty global config.
            os.environ["GIT_CONFIG_GLOBAL"] = str(config)
            # Never read system Git configuration or its configured helpers.
            os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
            os.environ.update(HOME=str(home), XDG_CONFIG_HOME=str(xdg),
                              TMPDIR=str(temporary_root), TMP=str(temporary_root),
                              TEMP=str(temporary_root))
            if os.name == "nt":
                os.environ["USERPROFILE"] = str(home)
            yield
        finally:
            for key in list(os.environ):
                if _managed(key):
                    del os.environ[key]
            os.environ.update(previous)


def _go_tests(root: Path, command: list[str]) -> int:
    from fixture_process import OwnedProcess, termination_event, wait_owned, watch_lease
    import shutil
    import subprocess

    # The outer Go process created this exclusive empty root and also owns
    # fallback cleanup if the provider dies. Never accept an ambient root.
    if (not root.is_absolute() or root.resolve(strict=True) != root
            or not root.name.startswith("curator-go-fixture-") or any(root.iterdir())):
        raise ValueError("Go fixture root must be an empty owned physical directory")
    try:
        os.environ["TMPDIR"] = str(root)
        with isolated_environment(), termination_event() as lost:
            watch_lease(sys.stdin.buffer, lost)
            process = OwnedProcess(command, stdin=subprocess.PIPE,
                                   stdout=sys.stderr, stderr=sys.stderr)
            try:
                print(json.dumps({"event": "started", "pid": process.child.pid}), flush=True)
                grant = {"version": 1, "root": str(Path(os.environ["HOME"]).parent),
                         "set": {k: v for k, v in os.environ.items() if _managed(k)}}
                process.child.stdin.write((json.dumps(grant) + "\n").encode())
                process.child.stdin.flush()
                status = wait_owned(process, lost)
            finally:
                process.stop()
                process.child.stdin.close()
        # Completion is emitted only after descendants and private homes are
        # gone. EOF or a provider exit code alone can never mean success.
        # An abrupt Go exit bypasses t.TempDir cleanup. The validated exclusive
        # outer root owns these sibling temp trees as well as the private HOME.
        shutil.rmtree(root)
        print(json.dumps({"event": "completed", "status": status}), flush=True)
        return status
    finally:
        # TemporaryDirectory handles its own tree; this root is exclusively
        # shared with the outer Go cleanup, so an already removed root is OK.
        try:
            shutil.rmtree(root)
        except FileNotFoundError:
            pass


def _command(command: list[str]) -> int:
    from fixture_process import OwnedProcess, WindowsStartGate, termination_event, wait_owned
    with isolated_environment(), termination_event() as lost:
        gate = WindowsStartGate() if os.name == "nt" else None
        try:
            if gate:
                command = [sys.executable, str(Path(__file__).with_name("fixture_process.py")),
                           "--wait", gate.name, *command]
            process = OwnedProcess(command)
            try:
                if gate:
                    gate.release()
                return wait_owned(process, lost)
            finally:
                process.stop()
        finally:
            if gate:
                gate.close()


def main() -> int:
    if len(sys.argv) == 1:
        raise SystemExit("usage: fixture_environment.py COMMAND [ARG ...]")
    if sys.argv[1] == "--go-test":
        if len(sys.argv) < 5:
            raise SystemExit("Go fixture supervision requires a root and child command")
        return _go_tests(Path(sys.argv[2]), sys.argv[3:])
    return _command(sys.argv[1:])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("fixture boundary:", type(error).__name__ + ":", error, file=sys.stderr, flush=True)
        raise SystemExit(2)
