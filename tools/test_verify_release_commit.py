from __future__ import annotations

import unittest

import verify_release_commit


COMMIT = "a" * 40


def github_payload() -> dict[str, object]:
    return {
        "sha": COMMIT,
        "commit": {
            "committer": {"name": "GitHub", "email": "noreply@github.com"},
            "verification": {
                "verified": True,
                "reason": "valid",
                "signature": "signed",
                "payload": "commit payload",
            },
        },
    }


class GitHubCommitVerificationTests(unittest.TestCase):
    def test_accepts_verified_github_commit(self) -> None:
        verify_release_commit.validate_github_payload(github_payload(), COMMIT)

    def test_rejects_different_commit(self) -> None:
        payload = github_payload()
        payload["sha"] = "b" * 40
        with self.assertRaisesRegex(verify_release_commit.VerificationFailure, "different release target"):
            verify_release_commit.validate_github_payload(payload, COMMIT)

    def test_rejects_non_github_committer(self) -> None:
        payload = github_payload()
        payload["commit"]["committer"] = {"name": "Other", "email": "other@example.invalid"}  # type: ignore[index]
        with self.assertRaisesRegex(verify_release_commit.VerificationFailure, "GitHub-created"):
            verify_release_commit.validate_github_payload(payload, COMMIT)

    def test_rejects_unverified_signature(self) -> None:
        payload = github_payload()
        payload["commit"]["verification"]["verified"] = False  # type: ignore[index]
        with self.assertRaisesRegex(verify_release_commit.VerificationFailure, "did not validate"):
            verify_release_commit.validate_github_payload(payload, COMMIT)

    def test_rejects_missing_signed_material(self) -> None:
        payload = github_payload()
        payload["commit"]["verification"]["signature"] = ""  # type: ignore[index]
        with self.assertRaisesRegex(verify_release_commit.VerificationFailure, "signed material"):
            verify_release_commit.validate_github_payload(payload, COMMIT)


# Real isolated SSH signatures prove source acceptance, containment and tag-scope
# separation. No live key, signing agent, user configuration or network is used.
class SourceTrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        cls.temporary = tempfile.TemporaryDirectory(prefix="source-provenance-")
        cls.root = Path(cls.temporary.name).resolve()
        for name in ("home", "tmp", "cache", "gopath", "programdata", "repo", "decoy"):
            (cls.root / name).mkdir()
        cls.repo = cls.root / "repo"
        cls.env = cls.fixture_environment(cls.root)
        cls.pid_log = os.environ.get("PROVENANCE_TEST_PID_LOG")
        cls.patch = patch.object(verify_release_commit, "ROOT", cls.repo)
        cls.patch.start()
        try:
            cls.run_child("git", "init", "-q", str(cls.repo))
            cls.run_child("git", "init", "-q", str(cls.root / "decoy"))
            cls.keys = {}
            for role in ("source", "release", "unknown"):
                key = cls.root / role
                cls.run_child("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key))
                cls.keys[role] = key
            source = cls.keys["source"].with_suffix(".pub").read_text().split()
            release = cls.keys["release"].with_suffix(".pub").read_text().split()
            cls.source_trust = 'source-commit namespaces="git" ' + " ".join(source[:2]) + "\n"
            cls.release_trust = "release-fixture " + " ".join(release[:2]) + "\n"
            (cls.repo / "source.allowed_signers").write_text(cls.source_trust)
            (cls.repo / "maintainers.allowed_signers").write_text(cls.release_trust)
            for key, value in (("gpg.format", "ssh"), ("gpg.ssh.program", "ssh-keygen"),
                               ("gpg.ssh.allowedSignersFile", str(cls.repo / "maintainers.allowed_signers"))):
                cls.run_child("git", "config", key, value)
            tree = cls.run_child("git", "mktree", input="").stdout.strip()
            cls.commits = {}
            parent = []
            for role in ("source", "release", "unknown", "unsigned"):
                signing = [] if role == "unsigned" else ["-c", f"user.signingkey={cls.keys[role]}"]
                signed = [] if role == "unsigned" else ["-S"]
                commit = cls.run_child("git", *signing, "commit-tree", tree, *signed, *parent,
                                       input=role + "\n").stdout.strip()
                cls.commits[role] = commit
                parent = ["-p", commit]
            cls.side = cls.run_child("git", "-c", f"user.signingkey={cls.keys['release']}",
                                     "commit-tree", tree, "-S", "-p", cls.commits["source"],
                                     input="uncontained\n").stdout.strip()
            cls.run_child("git", "update-ref", "refs/remotes/origin/main", cls.commits["unsigned"])
            cls.run_child("git", "update-ref", "HEAD", cls.commits["unsigned"])
        except BaseException:
            cls.patch.stop()
            cls.temporary.cleanup()
            raise

    @staticmethod
    def fixture_environment(root):
        import os
        env = {
            "PATH": os.defpath + os.pathsep + os.environ.get("PATH", ""),
            "HOME": str(root / "home"), "TMPDIR": str(root / "tmp"),
            "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"),
            "XDG_CONFIG_HOME": str(root / "home" / "config"),
            "XDG_CACHE_HOME": str(root / "cache"),
            # Win32-OpenSSH initializes ProgramData before keygen main. Pin it
            # to this fixture, never the caller's machine-wide SSH directory.
            "ProgramData": str(root / "programdata"),
            # Native OpenSSH otherwise invents the machine's default agent pipe.
            # Signing may probe only this nonexistent fixture-owned socket.
            "SSH_AUTH_SOCK": str(root / "no-agent.sock"),
            "GOPATH": str(root / "gopath"),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull, "LC_ALL": "C",
            "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
        if "SYSTEMROOT" in os.environ:
            env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        return env

    @classmethod
    def run_child(cls, *args: str, input: str | None = None, check: bool = True):
        import shutil
        import subprocess
        from pathlib import Path

        executable = shutil.which(args[0], path=cls.env["PATH"])
        if executable is None:
            raise AssertionError("fixture executable unavailable")
        tool = Path(executable)
        family = "windows-openssh" if tool.parent.name.lower() == "openssh" else "path-resolved"
        identity = f"{family}/{tool.name}"
        launch_failure = None
        try:
            process = subprocess.Popen((executable, *args[1:]), cwd=cls.repo, env=cls.env,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        except OSError as error:
            launch_failure = type(error).__name__
        # Raise outside the handler: suppressing display alone retains context.
        if launch_failure is not None:
            raise AssertionError(f"fixture child could not start: {identity}: {launch_failure}")
        if cls.pid_log:
            with open(cls.pid_log, "a") as log:
                log.write(f"{process.pid} {args[0]}\n")
        timeout_counts = None
        try:
            stdout, stderr = process.communicate(input, timeout=10)
        except subprocess.TimeoutExpired as error:
            timeout_counts = []
            for stream, value in (("stdout", error.output), ("stderr", error.stderr)):
                if value is None:
                    timeout_counts.append(f"partial_{stream}=unavailable")
                else:
                    unit = "bytes" if isinstance(value, bytes) else "chars"
                    timeout_counts.append(f"partial_{stream}_{unit}={len(value)}")
        except BaseException:
            # Preserve interruption/unexpected-error semantics after exact-child
            # cleanup; only expected launch/timeout errors are normalized.
            process.kill()
            process.wait(timeout=5)
            raise
        if timeout_counts is not None:
            # The timeout handler has ended before cleanup or replacement is
            # raised, so neither error can retain the raw TimeoutExpired.
            cleanup_failure = None
            stage = "kill"
            try:
                process.kill()
                stage = "reap"
                status = process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired) as error:
                cleanup_failure = f"{stage}:{type(error).__name__}"
            counts = "; ".join(timeout_counts)
            if cleanup_failure is not None:
                raise AssertionError(f"fixture child timed out: {identity}: timeout=10; "
                                     f"cleanup=unconfirmed({cleanup_failure}); {counts}")
            raise AssertionError(f"fixture child timed out: {identity}: timeout=10; "
                                 f"exit={status}; cleanup=reaped; {counts}")
        result = subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
        if check and result.returncode:
            # Tool output can contain keys or other sensitive inputs. Report
            # bounded metadata only, including silent Windows startup failures.
            raise AssertionError(f"fixture child failed: {identity}: exit={result.returncode}; "
                                 f"stdout_chars={len(stdout)}; stderr_chars={len(stderr)}")
        return result

    @classmethod
    def tearDownClass(cls) -> None:
        cls.patch.stop()
        cls.temporary.cleanup()

    def invoke(self, commit: str, poison: dict[str, str] | None = None):
        import contextlib
        import io
        from unittest.mock import patch
        output = io.StringIO()
        import subprocess
        popen = subprocess.Popen
        def recorded_popen(*args, **kwargs):
            process = popen(*args, **kwargs)
            if self.pid_log:
                with open(self.pid_log, "a") as log:
                    log.write(f"{process.pid} verifier git\n")
            return process
        with patch.dict("os.environ", {**self.env, **(poison or {})}, clear=True), \
             patch("sys.argv", ["verify_release_commit.py", "--commit", commit]), \
             patch.object(subprocess, "Popen", side_effect=recorded_popen), \
             patch.object(verify_release_commit, "fetch_github_payload", side_effect=
                          verify_release_commit.VerificationFailure("API fallback not permitted in SSH control")), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = verify_release_commit.main()
        return status, output.getvalue()

    def test_accepts_source_and_existing_release_signers(self) -> None:
        for role in ("source", "release"):
            with self.subTest(role=role):
                status, output = self.invoke(self.commits[role])
                self.assertEqual(status, 0, output)

    def test_rejects_unknown_and_unsigned(self) -> None:
        for role, reason in (("unknown", "no authorized SSH signature"),
                             ("unsigned", "lacks supported signed material")):
            with self.subTest(role=role):
                status, output = self.invoke(self.commits[role])
                self.assertEqual(status, 1, output)
                self.assertIn(reason, output)

    def test_rejects_uncontained_signed_commit(self) -> None:
        status, output = self.invoke(self.side)
        self.assertEqual(status, 1, "uncontained authorized signature was accepted: " + output)
        self.assertIn("not contained", output)

    def test_hostile_config_cannot_grant_unknown_key(self) -> None:
        unknown = self.keys["unknown"].with_suffix(".pub").read_text().split()
        ambient = self.root / "ambient-signers"
        ambient.write_text("unknown " + " ".join(unknown[:2]) + "\n")
        poison = {"GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "gpg.format",
                  "GIT_CONFIG_VALUE_0": "ssh", "GIT_CONFIG_KEY_1": "gpg.ssh.allowedSignersFile",
                  "GIT_CONFIG_VALUE_1": str(ambient)}
        status, output = self.invoke(self.commits["unknown"], poison)
        self.assertEqual(status, 1, "ambient key was accepted: " + output)
        self.assertIn("no authorized SSH signature", output)
        # Poisoned repository/trace selectors are cleared without touching the decoy.
        trace = self.root / "external-trace"
        import hashlib
        def snapshot():
            return {str(p.relative_to(self.root / "decoy")):
                    (tuple(getattr(p.lstat(), name) for name in
                           ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
                            "st_size", "st_mtime_ns", "st_ctime_ns")),
                     hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None)
                    for p in (self.root / "decoy").rglob("*")}
        before = snapshot()
        poison.update({"GIT_DIR": str(self.root / "decoy" / ".git"),
                       "GIT_WORK_TREE": str(self.root / "decoy"), "GIT_TRACE": str(trace)})
        self.assertEqual(self.invoke(self.commits["source"], poison)[0], 0)
        self.assertFalse(trace.exists())
        self.assertEqual(before, snapshot())

    def test_missing_ref_and_wrong_target_refuse(self) -> None:
        self.run_child("git", "update-ref", "-d", "refs/remotes/origin/main")
        try:
            status, output = self.invoke(self.commits["source"])
            self.assertEqual(status, 1, output)
            self.assertIn("show-ref", output)
        finally:
            self.run_child("git", "update-ref", "refs/remotes/origin/main", self.commits["unsigned"])
        status, output = self.invoke("0" * 40)
        self.assertEqual(status, 1, output)
        self.assertIn("rev-parse", output)

    def test_invalid_source_trust_refuses_even_release_signer(self) -> None:
        path = self.repo / "source.allowed_signers"
        try:
            for invalid in ("", self.source_trust + self.source_trust,
                            self.source_trust.replace('namespaces="git"', 'namespaces="*"'),
                            'source-commit namespaces="git" ssh-ed25519 AAAA\n'):
                path.write_text(invalid)
                status, output = self.invoke(self.commits["release"])
                self.assertEqual(status, 1, output)
                self.assertIn("trust", output)
            path.unlink()
            path.mkdir()
            self.assertEqual(self.invoke(self.commits["release"])[0], 1)
        finally:
            if path.is_dir():
                path.rmdir()
            else:
                path.unlink(missing_ok=True)
            path.write_text(self.source_trust)

    def test_source_key_cannot_endorse_release_tag(self) -> None:
        for role in ("source", "release"):
            self.run_child("git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                           "-c", f"user.signingkey={self.keys[role]}", "tag", "-s", "-m", role,
                           role + "-tag", self.commits["source"])
            process = self.run_child("git", "-c", "gpg.format=ssh", "-c", "gpg.ssh.program=ssh-keygen",
                                     "-c", f"gpg.ssh.allowedSignersFile={self.repo / 'maintainers.allowed_signers'}",
                                     "verify-tag", role + "-tag", check=False)
            stderr = process.stderr
            self.assertEqual(process.returncode, 0 if role == "release" else 1, stderr)
            if role == "source":
                self.assertIn("No principal matched", stderr)
            target = self.run_child("git", "rev-parse", role + "-tag^{commit}").stdout.strip()
            self.assertEqual(target, self.commits["source"])
            self.assertNotEqual(target, self.commits["release"], "wrong target must not match endorsement")


# These controls prove fixture-only environment isolation and safe failure
# receipts. Real SourceTrustTests above still prove actual keygen/signatures;
# local subprocess controls do not qualify native Windows startup.
class SourceFixtureHarnessTests(unittest.TestCase):
    def test_programdata_is_owned_and_host_environment_excluded(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        poison = {name: "foreign-synthetic" for name in (
            "GIT_DIR", "GIT_WORK_TREE", "GIT_FOO_BAR", "GIT_CONFIG_COUNT", "GIT_TRACE",
            "XDG_FOO_BAR", "XDG_CONFIG_HOME", "SSH_AUTH_SOCK", "SSH_ASKPASS", "GOFLAGS",
            "CODEX_HOME", "CLAUDE_CONFIG_DIR", "USERPROFILE", "APPDATA", "LOCALAPPDATA")}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with patch.dict(os.environ, {**poison, "ProgramData": "foreign-machine-ssh",
                                        "PATH": os.defpath, "SYSTEMROOT": "synthetic-system"}, clear=True):
                env = SourceTrustTests.fixture_environment(root)
            self.assertEqual(env["ProgramData"], str(root / "programdata"))
            self.assertTrue(Path(env["ProgramData"]).is_absolute())
            self.assertNotIn("foreign", " ".join(env.values()))
            for name in ("HOME", "TMP", "TEMP", "TMPDIR", "GOPATH", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
                self.assertTrue(Path(env[name]).is_relative_to(root), name)
            for name in poison:
                if name not in {"XDG_CONFIG_HOME", "GIT_CONFIG_COUNT", "SSH_AUTH_SOCK"}:
                    self.assertNotIn(name, env)
            self.assertEqual(env["SSH_AUTH_SOCK"], str(root / "no-agent.sock"))
            self.assertFalse(Path(env["SSH_AUTH_SOCK"]).exists())
            self.assertNotIn("GIT_CONFIG_COUNT", env)
            self.assertEqual(env["SYSTEMROOT"], "synthetic-system")

    def test_failure_receipt_has_exit_and_no_raw_child_output(self):
        import os
        import sys
        import tempfile
        import traceback
        import uuid
        from pathlib import Path
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context = SimpleNamespace(repo=root, env=SourceTrustTests.fixture_environment(root),
                                      pid_log=os.environ.get("PROVENANCE_TEST_PID_LOG"))
            secret = "synthetic-" + uuid.uuid4().hex
            message = diagnostics = ""
            try:
                SourceTrustTests.run_child.__func__(context, sys.executable, "-c",
                    "import sys; s=sys.stdin.read(); sys.stdout.write(s); sys.stderr.write(s); sys.exit(7)",
                    input=secret)
            except AssertionError as error:
                message = str(error)
                diagnostics = "".join(traceback.format_exception(error))
            self.assertNotIn(secret, message + diagnostics, "fixture output reflected in failure")
            self.assertIn("exit=7", message)
            self.assertIn("path-resolved/", message)
            self.assertIn(f"stdout_chars={len(secret)}; stderr_chars={len(secret)}", message)
            # A silent failure must still report status, rather than an empty
            # diagnostic like the original Windows failed-step output.
            with self.assertRaisesRegex(AssertionError, r"exit=9; stdout_chars=0; stderr_chars=0"):
                SourceTrustTests.run_child.__func__(context, sys.executable, "-c", "raise SystemExit(9)")
            valid = SourceTrustTests.run_child.__func__(context, sys.executable, "-c", "print('fixture-ready')")
            self.assertEqual((valid.returncode, valid.stdout), (0, "fixture-ready\n"))

    def test_missing_or_unlaunchable_tool_refuses_explicitly(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context = SimpleNamespace(repo=root, env={"PATH": str(root)}, pid_log=None)
            with patch("subprocess.Popen") as launch:
                with self.assertRaisesRegex(AssertionError, "^fixture executable unavailable$"):
                    SourceTrustTests.run_child.__func__(context, "nonexistent-fixture-tool")
                launch.assert_not_called()
            with patch("shutil.which", return_value=str(root / "OpenSSH" / "ssh-keygen.exe")), \
                 patch("subprocess.Popen", side_effect=PermissionError("synthetic-sensitive-output")):
                with self.assertRaisesRegex(AssertionError,
                        "^fixture child could not start: windows-openssh/ssh-keygen.exe: PermissionError$"):
                    SourceTrustTests.run_child.__func__(context, "ssh-keygen")


# Expected launch/timeout failures expose only safe metadata and no retained
# raw exception fields/context. The timeout reaches the real 10s bound; cleanup
# faults and interruptions are controlled call-state tests, not native proof.
class ExpectedFixtureErrorTests(unittest.TestCase):
    @staticmethod
    def capture_failure(call, fragments):
        import traceback
        snapshot = {"kind": None, "message": "", "unsafe": False,
                    "chained": False, "raw_fields": False}
        try:
            call()
        except Exception as error:
            raw_fields = ("cmd", "output", "stdout", "stderr", "filename", "filename2")
            rendered = (str(error) + repr(error) + repr(error.args) + repr(vars(error))
                        + "".join(traceback.format_exception(error))
                        + repr(error.__context__) + repr(error.__cause__)
                        + "".join(repr(getattr(error, name, None)) for name in raw_fields))
            snapshot = {"kind": type(error), "message": str(error),
                        "unsafe": any(part in rendered for part in fragments),
                        "chained": error.__cause__ is not None or error.__context__ is not None,
                        "raw_fields": any(hasattr(error, name) for name in raw_fields)}
        return snapshot

    def assert_safe_failure(self, snapshot):
        # Assert after the original handler. Failure output contains only safe
        # classifications, never generated values or their raw exception repr.
        self.assertFalse(snapshot["unsafe"], "expected fixture error retains sensitive data")
        self.assertFalse(snapshot["chained"], "expected fixture error retains context/cause")
        self.assertFalse(snapshot["raw_fields"], "expected fixture error retains raw subprocess fields")
        self.assertIs(snapshot["kind"], AssertionError)

    def test_launch_failure_has_no_sensitive_exception_state(self):
        import tempfile
        import uuid
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch

        marker = "synthetic-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context = SimpleNamespace(repo=root, env={"PATH": str(root)}, pid_log=None)
            with patch("shutil.which", return_value=str(root / "OpenSSH" / "ssh-keygen.exe")), \
                 patch("subprocess.Popen", side_effect=PermissionError(13, marker, marker)):
                snapshot = self.capture_failure(
                    lambda: SourceTrustTests.run_child.__func__(context, "ssh-keygen"), (marker,))
            self.observation = {key: snapshot[key] for key in ("unsafe", "chained", "raw_fields")}
            self.assert_safe_failure(snapshot)
            self.assertEqual(snapshot["message"],
                "fixture child could not start: windows-openssh/ssh-keygen.exe: PermissionError")

    def test_real_timeout_is_safe_and_exact_child_reaped(self):
        import os
        import subprocess
        import sys
        import tempfile
        import time
        import uuid
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock, patch

        argv_marker = "synthetic-argv-" + uuid.uuid4().hex
        stream_marker = "synthetic-stream-" + uuid.uuid4().hex
        processes = []
        partial_streams = {}
        popen = subprocess.Popen
        def tracked(*args, **kwargs):
            process = popen(*args, **kwargs)
            communicate = process.communicate
            def observed_communicate(input, *, timeout):
                try:
                    return communicate(input, timeout=timeout)
                except subprocess.TimeoutExpired as error:
                    for stream, value in (("stdout", error.output), ("stderr", error.stderr)):
                        partial_streams[stream] = (None if value is None else
                            ("bytes" if isinstance(value, bytes) else "chars", len(value)))
                    raise
            process.communicate = Mock(side_effect=observed_communicate)
            process.kill = Mock(wraps=process.kill)
            process.wait = Mock(wraps=process.wait)
            processes.append(process)
            return process
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context = SimpleNamespace(repo=root, env=SourceTrustTests.fixture_environment(root),
                                      pid_log=os.environ.get("PROVENANCE_TEST_PID_LOG"))
            # Nearby real success and explicit check=False data are preserved.
            valid = SourceTrustTests.run_child.__func__(context, sys.executable, "-c", "print('fixture-ready')")
            self.assertEqual((valid.returncode, valid.stdout), (0, "fixture-ready\n"))
            unchecked = SourceTrustTests.run_child.__func__(context, sys.executable, "-c",
                "import sys; sys.stdout.write(sys.stdin.read()); sys.exit(7)", input=stream_marker, check=False)
            self.assertTrue(unchecked.returncode == 7 and unchecked.stdout == stream_marker,
                            "check=False must preserve explicit nonzero data")
            ready = root / "ready"
            try:
                with patch.object(subprocess, "Popen", side_effect=tracked):
                    started = time.monotonic()
                    snapshot = self.capture_failure(lambda: SourceTrustTests.run_child.__func__(
                        context, sys.executable, "-c",
                        "import pathlib,sys,time; s=sys.stdin.read(); sys.stdout.write(s); sys.stdout.flush(); "
                        "sys.stderr.write(s); sys.stderr.flush(); pathlib.Path(sys.argv[1]).write_text('ready'); time.sleep(60)",
                        str(ready), argv_marker, input=stream_marker), (argv_marker, stream_marker))
                    elapsed = time.monotonic() - started
                self.assertEqual(len(processes), 1)
                process = processes[0]
                self.assertTrue(ready.is_file() and ready.read_text() == "ready", "real child did not reach body")
                self.assertGreaterEqual(elapsed, 9.5, "control did not reach actual communicate deadline")
                self.assertIsNotNone(process.returncode, "exact child was not reaped before owner return")
                process.kill.assert_called_once_with()
                process.wait.assert_called_once_with(timeout=5)
                self.assertEqual(process.communicate.call_count, 1)
                self.assertEqual(process.communicate.call_args.kwargs, {"timeout": 10})
                self.observation = {"pid": process.pid, "elapsed_seconds": elapsed,
                    "body_ready": True, "reaped": True, "exit": process.returncode,
                    "partial_streams": partial_streams,
                    **{key: snapshot[key] for key in ("unsafe", "chained", "raw_fields")}}
                self.assert_safe_failure(snapshot)
                message = snapshot["message"]
                self.assertIn("fixture child timed out: path-resolved/", message)
                self.assertIn(f"timeout=10; exit={process.returncode}; cleanup=reaped", message)
                # Windows may provide no partial fields even after the child
                # flushed. Match independently observed API availability, not
                # a platform assumption or guessed emitted-byte count.
                self.assertEqual(set(partial_streams), {"stdout", "stderr"})
                for stream, partial in partial_streams.items():
                    if partial is None:
                        self.assertIn(f"partial_{stream}=unavailable", message)
                    else:
                        unit, count = partial
                        self.assertEqual(count, len(stream_marker))
                        self.assertIn(f"partial_{stream}_{unit}={count}", message)
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)
                    for stream in (process.stdin, process.stdout, process.stderr):
                        if stream is not None:
                            stream.close()
        self.assertFalse(root.exists(), "owned timeout fixture not removed")

    def test_timeout_cleanup_failures_remain_unconfirmed(self):
        import subprocess
        import tempfile
        import uuid
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock, patch

        marker = "synthetic-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context = SimpleNamespace(repo=root, env={"PATH": str(root)}, pid_log=None)
            for stage, partial in (("kill", None), ("reap", b""),
                                   ("reap", marker.encode()), ("reap", marker)):
                with self.subTest(stage=stage, data_kind=type(partial).__name__):
                    process = Mock(returncode=None)
                    process.communicate.side_effect = subprocess.TimeoutExpired([marker], 10,
                        output=partial, stderr=partial)
                    if stage == "kill":
                        process.kill.side_effect = PermissionError(marker)
                    else:
                        process.wait.side_effect = subprocess.TimeoutExpired([marker], 5, output=marker.encode())
                    with patch("shutil.which", return_value=str(root / "fixture-tool")), \
                         patch("subprocess.Popen", return_value=process):
                        snapshot = self.capture_failure(lambda: SourceTrustTests.run_child.__func__(
                            context, "fixture-tool", check=False), (marker,))
                    self.assert_safe_failure(snapshot)
                    self.assertIn("cleanup=unconfirmed", snapshot["message"])
                    self.assertIn(stage + ":" + ("PermissionError" if stage == "kill" else "TimeoutExpired"),
                                  snapshot["message"])
                    self.assertNotIn("exit=", snapshot["message"])
                    self.assertNotIn("cleanup=reaped", snapshot["message"])
                    for stream in ("stdout", "stderr"):
                        if partial is None:
                            self.assertIn(f"partial_{stream}=unavailable", snapshot["message"])
                        else:
                            unit = "bytes" if isinstance(partial, bytes) else "chars"
                            self.assertIn(f"partial_{stream}_{unit}={len(partial)}", snapshot["message"])
                    process.kill.assert_called_once_with()
                    if stage == "kill":
                        process.wait.assert_not_called()
                    else:
                        process.wait.assert_called_once_with(timeout=5)

    def test_interruption_preserves_original_signal_after_cleanup(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock, patch

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context = SimpleNamespace(repo=root, env={"PATH": str(root)}, pid_log=None)
            for interruption in (KeyboardInterrupt(), SystemExit(7)):
                with self.subTest(kind=type(interruption).__name__):
                    process = Mock()
                    process.communicate.side_effect = interruption
                    observed = None
                    with patch("shutil.which", return_value=str(root / "fixture-tool")), \
                         patch("subprocess.Popen", return_value=process):
                        try:
                            SourceTrustTests.run_child.__func__(context, "fixture-tool")
                        except BaseException as error:
                            observed = error
                    self.assertIs(observed, interruption)
                    process.communicate.assert_called_once_with(None, timeout=10)
                    process.kill.assert_called_once_with()
                    process.wait.assert_called_once_with(timeout=5)


# API cases exercise delegated platform verification, not local PGP cryptography.
class SourcePolicyTests(unittest.TestCase):
    def invoke(self, *, kind="github", payload=None, failure=None, context=None):
        import contextlib
        import io
        from unittest.mock import patch
        output = io.StringIO()
        with patch.dict("os.environ", {"GITHUB_TOKEN": "fixture-token", **(context or {})}, clear=True), \
             patch("sys.argv", ["verify_release_commit.py", "--commit", COMMIT]), \
             patch.object(verify_release_commit, "resolve_commit", return_value=COMMIT), \
             patch.object(verify_release_commit, "require_default_branch_ancestor") as ancestor, \
             patch.object(verify_release_commit, "commit_signature_kind", return_value=kind) as signature, \
             patch.object(verify_release_commit, "fetch_github_payload", return_value=payload,
                          side_effect=failure) as fetch, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = verify_release_commit.main()
        return status, output.getvalue(), ancestor, signature, fetch

    def test_github_route_requires_exact_verified_material(self) -> None:
        valid = github_payload()
        self.assertEqual(self.invoke(payload=valid)[0], 0)
        for changed in (None, {}, {"sha": "b" * 40}):
            self.assertEqual(self.invoke(payload=changed)[0], 1)
        for key, value, reason in (("signature", [], "signed material"),
                                   ("payload", {"text": "x"}, "signed material"),
                                   ("verified", 1, "did not validate"),
                                   ("reason", "unknown_key", "did not validate")):
            payload = github_payload()
            payload["commit"]["verification"][key] = value
            status, output, *_ = self.invoke(payload=payload)
            self.assertEqual(status, 1, output)
            self.assertIn(reason, output)

    def test_ambiguous_api_and_context_refuse(self) -> None:
        failure = verify_release_commit.VerificationFailure("could not read GitHub commit verification")
        self.assertEqual(self.invoke(failure=failure)[0], 1)
        for name in ("GITHUB_REPOSITORY", "GITHUB_DEFAULT_BRANCH", "GITHUB_API_URL"):
            status, output, ancestor, signature, fetch = self.invoke(payload=github_payload(), context={name: "other"})
            self.assertEqual(status, 1, output)
            self.assertIn("does not match repository policy", output)
            ancestor.assert_not_called()
            signature.assert_not_called()
            fetch.assert_not_called()

    def test_cli_trust_root_overrides_are_not_supported(self) -> None:
        import contextlib
        import io
        from unittest.mock import patch
        for flag in ("--api-url", "--repository", "--default-branch"):
            with patch("sys.argv", ["verify_release_commit.py", flag, "other"]), \
                 contextlib.redirect_stderr(io.StringIO()), \
                 patch.object(verify_release_commit, "git") as git:
                with self.assertRaises(SystemExit) as refusal:
                    verify_release_commit.main()
                self.assertEqual(refusal.exception.code, 2)
                git.assert_not_called()

    def test_transport_is_fixed_bounded_and_refuses_errors(self) -> None:
        import io
        import json
        import urllib.error
        from unittest.mock import Mock, patch
        opener = Mock()
        response = io.BytesIO(json.dumps(github_payload()).encode())
        opener.open.return_value = response
        with patch.object(verify_release_commit.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(verify_release_commit.fetch_github_payload(COMMIT, "fixture-token"), github_payload())
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.github.com/repos/relux-works/curator-spec/commits/" + COMMIT)
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 30})
        for error in (OSError("network"), urllib.error.HTTPError(request.full_url, 302, "redirect", {}, None)):
            opener.open.side_effect = error
            with patch.object(verify_release_commit.urllib.request, "build_opener", return_value=opener):
                with self.assertRaisesRegex(verify_release_commit.VerificationFailure, "could not read"):
                    verify_release_commit.fetch_github_payload(COMMIT, "fixture-token")
            if isinstance(error, urllib.error.HTTPError):
                error.close()
        self.assertIsNone(verify_release_commit.NoRedirect().redirect_request(request, None, 302, "redirect", {}, "https://other.invalid"))
        with self.assertRaisesRegex(verify_release_commit.VerificationFailure, "GITHUB_TOKEN"):
            verify_release_commit.fetch_github_payload(COMMIT, "")


# Both consumers must reject credential-bearing header/transport failures with
# stable public diagnostics. HTTP is parsed in memory; no TLS/network is proved.
class SecretFreeTransportMixin:
    def fetch(self, token):
        raise NotImplementedError

    def invoke_main(self, token):
        raise NotImplementedError

    def assert_safe_refusal(self, call, fragments):
        import traceback
        exception_type = None
        message = diagnostics = ""
        chained = False
        try:
            call()
        except Exception as error:
            exception_type = type(error)
            message = str(error)
            diagnostics = repr(error) + "\n" + "".join(traceback.format_exception(error))
            chained = error.__context__ is not None or error.__cause__ is not None
        # Assert after leaving the handler so a failed detector never prints the
        # underlying credential-bearing exception as its own context.
        self.assertFalse(any(part in diagnostics for part in fragments),
                         "credential reflected in helper diagnostics")
        self.assertFalse(chained, "raw transport error remains chained")
        self.assertIs(exception_type, self.failure_type)
        self.assertEqual(message, self.failure_message)

    def test_malformed_header_is_secret_free_before_connect(self):
        import http.client
        import os
        from unittest.mock import patch
        import uuid
        first, second = "synthetic-" + uuid.uuid4().hex, "tail-" + uuid.uuid4().hex
        token = first + "\n" + second
        rejected = []
        putheader = http.client.HTTPConnection.putheader
        def observed_header(connection, header, *values):
            try:
                return putheader(connection, header, *values)
            except ValueError:
                rejected.append(True)
                raise
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(http.client.HTTPConnection, "putheader", new=observed_header), \
             patch.object(http.client.HTTPSConnection, "connect", side_effect=AssertionError("connect forbidden")) as connect:
            with self.subTest(channel="helper"):
                self.assert_safe_refusal(lambda: self.fetch(token), (first, second))
            status, output = self.invoke_main(token)
            with self.subTest(channel="stderr"):
                self.assertFalse(any(part in output for part in (first, second, "Bearer", "Authorization")),
                                 "credential reflected in public stderr")
                self.assertEqual(status, 1)
                self.assertEqual(output, self.public_failure + "\n")
            connect.assert_not_called()
        self.assertEqual(len(rejected), 2, "both calls must reach actual HTTP header rejection")

    def test_transport_errors_discard_sensitive_exception_details(self):
        import http.client
        import os
        import urllib.error
        from unittest.mock import patch
        import uuid
        secret = "synthetic-" + uuid.uuid4().hex
        for error_type in (OSError, urllib.error.URLError, ValueError, http.client.BadStatusLine):
            with self.subTest(error_type=error_type.__name__), patch.dict(os.environ, {}, clear=True), \
                 patch.object(verify_release_commit.urllib.request, "build_opener", side_effect=error_type(secret)):
                with self.subTest(channel="helper"):
                    self.assert_safe_refusal(lambda: self.fetch("fixture-token"), (secret,))
                status, output = self.invoke_main("fixture-token")
                with self.subTest(channel="stderr"):
                    self.assertFalse(secret in output, "credential reflected in public stderr")
                    self.assertEqual((status, output), (1, self.public_failure + "\n"))

    def test_real_http_parser_positive_and_redirect_refusals(self):
        import http.client
        import io
        import json
        import os
        from unittest.mock import patch
        connections = []
        response_bytes = b""
        class MemorySocket:
            def sendall(self, data):
                pass
            def makefile(self, *args, **kwargs):
                return io.BytesIO(response_bytes)
            def close(self):
                pass
        def connect(connection):
            connections.append((connection.host, connection.port, connection.timeout))
            connection.sock = MemorySocket()
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(http.client.HTTPSConnection, "connect", new=connect):
            payload = self.valid_payload()
            data = json.dumps(payload).encode()
            response_bytes = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(data)).encode() + b"\r\nConnection: close\r\n\r\n" + data
            self.assertEqual(self.fetch("fixture-token"), payload)
            status, output = self.invoke_main("fixture-token")
            self.assertEqual(status, 0, "nearby valid API response refused")
            self.assertIn(self.valid_output, output)
            self.assertEqual(connections, [("api.github.com", 443, 30)] * 2)
            for code in (301, 302, 303, 307, 308):
                with self.subTest(code=code):
                    connections.clear()
                    response_bytes = f"HTTP/1.1 {code} Redirect\r\nLocation: https://other.invalid/\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".encode()
                    self.assert_safe_refusal(lambda: self.fetch("fixture-token"), ())
                    self.assertEqual(connections, [("api.github.com", 443, 30)],
                                     "redirect contacted another authority")


class SecretFreeCommitTransportTests(SecretFreeTransportMixin, unittest.TestCase):
    failure_type = verify_release_commit.VerificationFailure
    failure_message = "could not read GitHub commit verification"
    public_failure = "release commit verification failed: " + failure_message
    valid_output = "is a GitHub-verified commit on origin/main"
    valid_payload = staticmethod(github_payload)

    def fetch(self, token):
        return verify_release_commit.fetch_github_payload(COMMIT, token)

    def invoke_main(self, token):
        import contextlib
        import io
        import os
        from unittest.mock import patch
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": token}, clear=True), \
             patch("sys.argv", ["verify_release_commit.py", "--commit", COMMIT]), \
             patch.object(verify_release_commit, "resolve_commit", return_value=COMMIT), \
             patch.object(verify_release_commit, "require_default_branch_ancestor"), \
             patch.object(verify_release_commit, "commit_signature_kind", return_value="github"), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                status = verify_release_commit.main()
            except Exception as error:
                import traceback
                output.write("".join(traceback.format_exception(error)))
                status = None
        return status, output.getvalue()


if __name__ == "__main__":
    unittest.main()
