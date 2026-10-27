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
        for name in ("home", "tmp", "cache", "gopath", "repo", "decoy"):
            (cls.root / name).mkdir()
        cls.repo = cls.root / "repo"
        cls.env = {
            "PATH": os.defpath + os.pathsep + os.environ.get("PATH", ""),
            "HOME": str(cls.root / "home"), "TMPDIR": str(cls.root / "tmp"),
            "TMP": str(cls.root / "tmp"), "TEMP": str(cls.root / "tmp"),
            "XDG_CONFIG_HOME": str(cls.root / "home" / "config"),
            "XDG_CACHE_HOME": str(cls.root / "cache"),
            "GOPATH": str(cls.root / "gopath"),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull, "LC_ALL": "C",
            "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
        if "SYSTEMROOT" in os.environ:
            cls.env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
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

    @classmethod
    def run_child(cls, *args: str, input: str | None = None, check: bool = True):
        import subprocess
        process = subprocess.Popen(args, cwd=cls.repo, env=cls.env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if cls.pid_log:
            with open(cls.pid_log, "a") as log:
                log.write(f"{process.pid} {args[0]}\n")
        try:
            stdout, stderr = process.communicate(input, timeout=10)
        except BaseException:
            process.kill()
            process.wait(timeout=5)
            raise
        result = subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
        if check and result.returncode:
            raise AssertionError(f"fixture child failed: {args[0]}: {stderr}")
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
        import os
        import urllib.error
        from unittest.mock import patch
        import uuid
        secret = "synthetic-" + uuid.uuid4().hex
        for error_type in (OSError, urllib.error.URLError, ValueError):
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
            status = verify_release_commit.main()
        return status, output.getvalue()


if __name__ == "__main__":
    unittest.main()
