"""Real fixture writes must stay in scratch repositories and homes."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fixture_environment import isolated_environment


class FixtureEnvironmentTests(unittest.TestCase):
    # The command runner uses the same boundary for non-unittest source-history
    # tools, cleans its homes, and preserves both success and failure statuses.
    def test_command_boundary_cleans_homes_and_preserves_exit_status(self):
        runner = Path(__file__).with_name("fixture_environment.py")
        script = (
            "import os, pathlib, sys; "
            "assert 'GIT_DIR' not in os.environ; "
            "assert 'SSH_AUTH_SOCK' not in os.environ; "
            "assert pathlib.Path(os.environ['HOME']).is_dir(); "
            "print(os.environ['HOME']); sys.exit(int(sys.argv[1]))"
        )
        for status in (0, 7):
            with self.subTest(status=status):
                child = subprocess.run(
                    [sys.executable, str(runner), sys.executable, "-c", script, str(status)],
                    env=dict(os.environ, GIT_DIR="hostile", SSH_AUTH_SOCK="hostile"),
                    capture_output=True, text=True)
                self.assertEqual(child.returncode, status, child.stderr)
                self.assertFalse(Path(child.stdout.strip()).exists())

    # All inherited selectors/config channels disappear; fixture native-home
    # writes stay private. Cleanup also restores unset versus empty values.
    def test_environment_and_home_are_isolated_and_restored_on_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            sentinel = home / ".claude" / "CLAUDE.md"
            sentinel.parent.mkdir()
            sentinel.write_text("operator", encoding="utf-8")
            poisoned = dict.fromkeys((
                "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG",
                "GIT_CONFIG_SYSTEM", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM",
                "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0",
                "GIT_CONFIG_PARAMETERS", "GIT_CEILING_DIRECTORIES", "SSH_AUTH_SOCK",
            ), "poison")
            poisoned.update(HOME=str(home), XDG_CONFIG_HOME="")
            with patch.dict(os.environ, poisoned):
                before = dict(os.environ)
                with self.assertRaisesRegex(RuntimeError, "cleanup witness"):
                    with isolated_environment():
                        isolated_home = Path(os.environ["HOME"])
                        self.assertEqual(Path.home(), isolated_home)
                        self.assertNotEqual(isolated_home, home)
                        self.assertTrue(Path(os.environ["XDG_CONFIG_HOME"]).is_dir())
                        for key in poisoned:
                            if key in {"HOME", "XDG_CONFIG_HOME", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"}:
                                continue
                            self.assertNotIn(key, os.environ)
                        self.assertEqual(Path(os.environ["GIT_CONFIG_GLOBAL"]).read_bytes(), b"")
                        self.assertEqual(os.environ["GIT_CONFIG_NOSYSTEM"], "1")
                        native = isolated_home / ".claude" / "CLAUDE.md"
                        native.parent.mkdir()
                        native.write_text("fixture", encoding="utf-8")
                        raise RuntimeError("cleanup witness")
                self.assertEqual(dict(os.environ), before)
                self.assertFalse(isolated_home.exists())
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "operator")

    # The real release fixture must commit successfully without changing the
    # hostile repository's refs, local config, or loose/packed object counts.
    def test_release_fixture_leaves_hostile_repository_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decoy = root / "decoy"
            decoy.mkdir()
            home = root / "operator-home"
            home.mkdir()
            env = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith("GIT_CONFIG")
                   and key.upper() not in {
                       "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                       "GIT_CEILING_DIRECTORIES", "SSH_AUTH_SOCK"}}
            env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "xdg"),
                       GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(home / "empty"))
            (home / "empty").touch()

            def git(*args):
                return subprocess.check_output(["git", *args], cwd=decoy, env=env)

            git("init", "-q")
            git("config", "fixture.sentinel", "preserved")
            git("-c", "user.name=Decoy", "-c", "user.email=decoy@example.invalid",
                "commit", "-qm", "decoy", "--allow-empty")

            def snapshot():
                return (git("show-ref"), (decoy / ".git" / "config").read_bytes(),
                        git("count-objects", "-v"))

            before = snapshot()
            hostile = dict(env, GIT_DIR=str(decoy / ".git"), GIT_WORK_TREE=str(decoy),
                           GIT_INDEX_FILE=str(decoy / ".git" / "index"),
                           GIT_CEILING_DIRECTORIES=str(root), SSH_AUTH_SOCK=str(root / "agent"),
                           GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="fixture.injected",
                           GIT_CONFIG_VALUE_0="hostile")
            child = subprocess.run(
                [sys.executable, "-B", "-m", "unittest", "-v",
                 "test_release_gate.StableReleaseGateTests."
                 "test_accepts_distinct_independent_reviewers_on_frozen_candidate"],
                cwd=Path(__file__).parent, env=hostile, capture_output=True, text=True)
            after = snapshot()
            for label, old, new in zip(("refs", "config", "objects"), before, after):
                self.assertEqual(old, new, f"decoy {label} changed:\n{child.stdout}{child.stderr}")
            self.assertEqual(child.returncode, 0, child.stdout + child.stderr)


if __name__ == "__main__":
    unittest.main()
