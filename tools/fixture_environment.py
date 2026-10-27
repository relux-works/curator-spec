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


# Keep aligned with curator internal/testgitenv (20-key repository, storage,
# discovery and template inventory). Bootstrap and command mode reuse this list.
REPOSITORY_SELECTORS = frozenset({
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE",
    "GIT_TEMPLATE_DIR", "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_SHALLOW_FILE",
    "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX",
    "GIT_QUARANTINE_PATH", "GIT_REFERENCE_BACKEND", "GIT_DEFAULT_HASH",
    "GIT_DEFAULT_REF_FORMAT",
})


def _managed(key: str) -> bool:
    key = key.upper()
    return key.startswith("GIT_CONFIG") or key in REPOSITORY_SELECTORS or key in {
        "SSH_AUTH_SOCK", "HOME", "XDG_CONFIG_HOME", "TMPDIR", "TMP", "TEMP",
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
    """Scrub inherited selectors, pin disposable homes, then restore the caller."""
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
            os.environ.update(HOME=str(home), XDG_CONFIG_HOME=str(xdg),
                              GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM="1",
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


if __name__ == "__main__":
    import subprocess

    if len(sys.argv) == 1:
        raise SystemExit("usage: fixture_environment.py COMMAND [ARG ...]")
    if sys.argv[1:] == ["--environment-json"]:
        # Direct Go TestMain consumes only this managed delta over a private
        # pipe. Keep the owning context alive until its stdin closes, including
        # when the test binary exits abruptly. No credentials are serialized.
        previous_keys = [key for key in os.environ if _managed(key)]
        with isolated_environment():
            print(json.dumps({"unset": previous_keys,
                              "set": {k: v for k, v in os.environ.items()
                                      if _managed(k)}}), flush=True)
            sys.stdin.buffer.read()
        raise SystemExit(0)
    # Source-history tools also need a discoverable checkout, not ambient Git
    # selectors. The fixture tests still enter their own module boundaries.
    with isolated_environment():
        raise SystemExit(subprocess.run(sys.argv[1:], check=False).returncode)
