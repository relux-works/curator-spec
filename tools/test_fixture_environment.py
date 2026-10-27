"""Real fixture writes must stay in scratch repositories and homes."""
from __future__ import annotations

import os
import hashlib
import json
import stat
import secrets
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fixture_environment import isolated_environment


# Independent regression inputs; the implementation uses a prefix, not this list.
REPOSITORY_SELECTORS = frozenset({
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE",
    "GIT_TEMPLATE_DIR", "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_SHALLOW_FILE",
    "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX",
    "GIT_QUARANTINE_PATH", "GIT_REFERENCE_BACKEND", "GIT_DEFAULT_HASH",
    "GIT_DEFAULT_REF_FORMAT",
})


class FixtureEnvironmentTests(unittest.TestCase):
    # Prefix scrubbing must cover unknown future keys and all F4/F5 channels;
    # only owned config defaults survive, while deliberate local tracing works.
    def test_git_prefix_scrub_and_fixture_local_trace(self):
        keys = ["GIT_FOO_BAR", "GIT_FOO_BAR_" + secrets.token_hex(8).upper(),
                "GIT_TRACE", "GIT_TRACE_SETUP", "GIT_TRACE2_EVENT",
                "GIT_ATTR_SOURCE", "GIT_INDEX_VERSION", "GIT_SSH", "GIT_SSH_COMMAND",
                "GIT_SSH_VARIANT", "GIT_ASKPASS", "SSH_AUTH_SOCK", "SSH_ASKPASS"]
        with patch.dict(os.environ, dict.fromkeys(keys, "poison")):
            before = dict(os.environ)
            with isolated_environment():
                for key in keys:
                    with self.subTest(key=key):
                        self.assertNotIn(key, os.environ)
                self.assertEqual({k for k in os.environ if k.startswith("GIT_")},
                                 {"GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"})
                home = Path(os.environ["HOME"])
                trace = home / "local.trace"
                os.environ["GIT_TRACE"] = str(trace)
                child = subprocess.run(["git", "init", "-q", str(home / "repo")],
                                       capture_output=True, text=True, timeout=10)
                self.assertEqual(child.returncode, 0, child.stderr)
                self.assertIn("built-in: git init", trace.read_text())
                os.environ["GIT_NEW_KEY_INSIDE"] = "owned"
            self.assertEqual(dict(os.environ), before)

    # Each inherited trace destination stays byte/identity identical while the
    # actual command wrapper creates a successful scratch repository commit.
    def test_inherited_trace_files_are_untouched(self):
        runner = Path(__file__).with_name("fixture_environment.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = root / "external.trace"
            trace.write_text("external sentinel")
            before = tree_snapshot(root)
            script = ("import os,pathlib,subprocess; "
                      "p=pathlib.Path(os.environ['HOME'])/'repo'; p.mkdir(); "
                      "subprocess.run(['git','init','-q',str(p)],check=True); "
                      "subprocess.run(['git','-C',str(p),'-c','user.name=Fixture',"
                      "'-c','user.email=fixture@example.invalid','commit','-qm','fixture',"
                      "'--allow-empty'],check=True)")
            for key in [None, "GIT_TRACE", "GIT_TRACE_SETUP", "GIT_TRACE2_EVENT"]:
                with self.subTest(key=key or "clean"):
                    env = dict(os.environ)
                    if key:
                        env[key] = str(trace.resolve())
                    child = subprocess.run([sys.executable, str(runner), sys.executable,
                                            "-c", script], env=env, capture_output=True,
                                           text=True, timeout=15)
                    self.assertEqual(child.returncode, 0, child.stderr)
                    self.assertEqual(tree_snapshot(root), before,
                                     "inherited trace modified external sentinel")

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

        trace = decoy / "external.trace"
        trace.write_text("external sentinel")
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
        expected.update({"GIT_TRACE", "GIT_TRACE_SETUP", "GIT_TRACE2_EVENT",
                         "GIT_ATTR_SOURCE", "GIT_INDEX_VERSION", "GIT_FOO_BAR"})
        values.update({k: str(trace.resolve()) for k in
                       ("GIT_TRACE", "GIT_TRACE_SETUP", "GIT_TRACE2_EVENT")})
        values.update(GIT_ATTR_SOURCE="HEAD", GIT_INDEX_VERSION="4", GIT_FOO_BAR="poison")
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
