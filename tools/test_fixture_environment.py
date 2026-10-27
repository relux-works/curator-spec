"""Real fixture writes must stay in scratch repositories and homes."""
from __future__ import annotations

import os
import hashlib
import json
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fixture_environment import REPOSITORY_SELECTORS, isolated_environment


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

    # The Go bridge must retain homes until EOF and remove them afterwards.
    # Its managed delta carries no inherited config payload or selector value.
    def test_environment_pipe_lifetime_and_selector_delta(self):
        runner = Path(__file__).with_name("fixture_environment.py")
        env = dict(os.environ, GIT_COMMON_DIR="hostile", GIT_CONFIG_VALUE_99="private")
        child = subprocess.Popen([sys.executable, str(runner), "--environment-json"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env, text=True)
        try:
            delta = json.loads(child.stdout.readline())
            self.assertIn("GIT_COMMON_DIR", delta["unset"])
            self.assertIn("GIT_CONFIG_VALUE_99", delta["unset"])
            self.assertNotIn("GIT_COMMON_DIR", delta["set"])
            self.assertNotIn("GIT_CONFIG_VALUE_99", delta["set"])
            home = Path(delta["set"]["HOME"])
            self.assertTrue(home.is_dir())
            self.assertIsNone(child.poll())
            child.stdin.close()
            self.assertEqual(child.wait(timeout=15), 0, child.stderr.read())
            self.assertFalse(home.exists())
        finally:
            if child.poll() is None:
                child.stdin.close()
                child.wait(timeout=15)
            child.stdout.close()
            child.stderr.close()

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
            poisoned.update(dict.fromkeys(REPOSITORY_SELECTORS, "poison"))
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

    # The real release fixture must succeed while every synthetic decoy path
    # retains its content hash and lstat identity, under each selector.
    def test_release_fixture_leaves_hostile_repository_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decoy = root / "decoy"
            decoy.mkdir()
            # Bootstrap uses the production boundary, not another scrub list.
            with isolated_environment():
                env = dict(os.environ)
                self._release_fixture_decoy(root, decoy, env)

    def _release_fixture_decoy(self, root, decoy, env):

        def git(*args):
            return subprocess.check_output(["git", *args], cwd=decoy, env=env)

        git("init", "-q")
        git("config", "fixture.sentinel", "preserved")
        git("-c", "user.name=Decoy", "-c", "user.email=decoy@example.invalid",
            "commit", "-qm", "decoy", "--allow-empty")

        before = tree_snapshot(decoy)
        # Every selector is independently injected. Each case must both admit
        # the real release fixture and preserve the full decoy byte/identity
        # inventory. The clean case is the neighboring positive control.
        values = {key: str(decoy / ".git") for key in REPOSITORY_SELECTORS}
        values.update(
            GIT_WORK_TREE=str(decoy), GIT_INDEX_FILE=str(decoy / ".git" / "index"),
            GIT_OBJECT_DIRECTORY=str(decoy / ".git" / "objects"),
            GIT_ALTERNATE_OBJECT_DIRECTORIES=str(decoy / ".git" / "objects"),
            GIT_QUARANTINE_PATH=str(decoy / ".git" / "objects"),
            GIT_CEILING_DIRECTORIES=str(root), GIT_DISCOVERY_ACROSS_FILESYSTEM="0",
            GIT_IMPLICIT_WORK_TREE="0", GIT_NO_REPLACE_OBJECTS="1",
            GIT_NAMESPACE="hostile", GIT_REPLACE_REF_BASE="refs/hostile/",
            GIT_REFERENCE_BACKEND="invalid-backend", GIT_DEFAULT_HASH="sha256",
            GIT_DEFAULT_REF_FORMAT="invalid-format", GIT_PREFIX="hostile/",
        )
        # This acceptance list is deliberately independent of the production
        # inventory: dropping one selector must not silently drop its control.
        expected = {
            "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE",
            "GIT_TEMPLATE_DIR", "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
            "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_SHALLOW_FILE",
            "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX",
            "GIT_QUARANTINE_PATH", "GIT_REFERENCE_BACKEND", "GIT_DEFAULT_HASH",
            "GIT_DEFAULT_REF_FORMAT",
        }
        self.assertEqual(REPOSITORY_SELECTORS, expected)
        for selector in [None, *sorted(expected)]:
            with self.subTest(selector=selector or "clean"):
                hostile = dict(env)
                if selector:
                    hostile[selector] = values[selector]
                # Check removal independently of whether a particular installed
                # Git version happens to honor the selector in this fixture.
                script = (
                    "import os, unittest; from fixture_environment import isolated_environment; "
                    "\nwith isolated_environment():\n assert os.environ.get('" + (selector or "GIT_DIR") + "') is None\n"
                    "suite=unittest.defaultTestLoader.loadTestsFromName("
                    "'test_release_gate.StableReleaseGateTests."
                    "test_accepts_distinct_independent_reviewers_on_frozen_candidate'); "
                    "result=unittest.TextTestRunner().run(suite); "
                    "raise SystemExit(not result.wasSuccessful())"
                )
                child = subprocess.run([sys.executable, "-B", "-c", script],
                                       cwd=Path(__file__).parent, env=hostile,
                                       capture_output=True, text=True)
                self.assertEqual(tree_snapshot(decoy), before,
                                 f"decoy changed under {selector}")
                self.assertEqual(child.returncode, 0, child.stdout + child.stderr)

    # Relative and symlink TMPDIR must produce physical absolute paths whose
    # cleanup still works after chdir. Missing explicit roots refuse setup.
    def test_temp_roots_are_physical_and_restore_caller(self):
        runner = Path(__file__).with_name("fixture_environment.py").resolve()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / ".tmp").mkdir()
            variants = [".tmp", str(root / ".tmp")]
            if os.name != "nt":
                (root / "alias").symlink_to(root / ".tmp", target_is_directory=True)
                variants.append("alias")
            script = (
                "import os,json,pathlib; "
                "keys=['HOME','XDG_CONFIG_HOME','GIT_CONFIG_GLOBAL','TMPDIR','TMP','TEMP']; "
                "paths={k:os.environ[k] for k in keys}; "
                "assert all(pathlib.Path(p).is_absolute() and str(pathlib.Path(p).resolve())==p "
                "for p in paths.values()); os.chdir(pathlib.Path(paths['HOME']).anchor); "
                "print(json.dumps(paths))"
            )
            for temporary in variants:
                with self.subTest(TMPDIR=temporary):
                    env = dict(os.environ, TMPDIR=temporary)
                    child = subprocess.run([sys.executable, str(runner), sys.executable,
                                            "-c", script], cwd=root, env=env,
                                           capture_output=True, text=True)
                    self.assertEqual(child.returncode, 0, child.stderr)
                    paths = json.loads(child.stdout)
                    self.assertFalse(Path(paths["HOME"]).exists())
                    self.assertEqual(paths["TMPDIR"], str(root / ".tmp"))
            child = subprocess.run([sys.executable, str(runner), sys.executable,
                                    "-c", "raise SystemExit('MUST NOT RUN')"], cwd=root,
                                   env=dict(os.environ, TMPDIR=str(root / "missing")),
                                   capture_output=True, text=True)
            self.assertNotEqual(child.returncode, 0)
            self.assertIn("FileNotFoundError", child.stderr)
            self.assertNotIn("MUST NOT RUN", child.stderr)


def tree_snapshot(root):
    """Synthetic decoy only: bytes plus lstat identity, never host credentials."""
    result = {}
    for path in [root, *sorted(root.rglob("*"))]:
        info = path.lstat()
        item = [info.st_mode, info.st_ino, info.st_size, info.st_mtime_ns]
        if stat.S_ISREG(info.st_mode):
            item.append(hashlib.sha256(path.read_bytes()).hexdigest())
        elif stat.S_ISLNK(info.st_mode):
            item.append(os.readlink(path))
        result[str(path.relative_to(root))] = item
    return result


if __name__ == "__main__":
    unittest.main()
