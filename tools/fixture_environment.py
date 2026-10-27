"""Shared process boundary for unittest modules that drive Git fixtures.

Install with unittest.enterModuleContext(isolated_environment()) in
setUpModule, before any fixture setup. Subprocesses (including validators)
then inherit the same safe defaults without patching subprocess or Git calls.
Tests may still provide explicit environment overrides inside that boundary.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile


def _managed(key: str) -> bool:
    key = key.upper()
    return key.startswith("GIT_CONFIG") or key in {
        "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CEILING_DIRECTORIES",
        "SSH_AUTH_SOCK", "HOME", "XDG_CONFIG_HOME",
    } or (os.name == "nt" and key == "USERPROFILE")


@contextmanager
def isolated_environment():
    """Scrub inherited selectors, pin disposable homes, then restore the caller."""
    previous = {key: value for key, value in os.environ.items() if _managed(key)}
    with tempfile.TemporaryDirectory(prefix="curator-test-environment-") as directory:
        root = Path(directory)
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
                              GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM="1")
            if os.name == "nt":
                os.environ["USERPROFILE"] = str(home)
            yield
        finally:
            for key in list(os.environ):
                if _managed(key):
                    del os.environ[key]
            os.environ.update(previous)
