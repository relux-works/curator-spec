from __future__ import annotations

import unittest

import verify_release_merge_policy
from test_verify_release_commit import SecretFreeTransportMixin


REPOSITORY = "relux-works/curator-spec"


def repository_payload() -> dict[str, object]:
    return {
        "full_name": REPOSITORY,
        "allow_squash_merge": True,
        "allow_rebase_merge": False,
        "allow_merge_commit": False,
    }


class ReleaseMergePolicyTests(unittest.TestCase):
    def test_accepts_squash_only_policy(self) -> None:
        verify_release_merge_policy.validate_repository_payload(repository_payload(), REPOSITORY)

    def test_rejects_different_repository(self) -> None:
        payload = repository_payload()
        payload["full_name"] = "other/project"
        with self.assertRaisesRegex(verify_release_merge_policy.PolicyFailure, "different repository"):
            verify_release_merge_policy.validate_repository_payload(payload, REPOSITORY)

    def test_rejects_disabled_squash_merging(self) -> None:
        payload = repository_payload()
        payload["allow_squash_merge"] = False
        with self.assertRaisesRegex(verify_release_merge_policy.PolicyFailure, "squash merging"):
            verify_release_merge_policy.validate_repository_payload(payload, REPOSITORY)

    def test_rejects_rebase_merging(self) -> None:
        payload = repository_payload()
        payload["allow_rebase_merge"] = True
        with self.assertRaisesRegex(verify_release_merge_policy.PolicyFailure, "rebase merging"):
            verify_release_merge_policy.validate_repository_payload(payload, REPOSITORY)

    def test_rejects_merge_commits(self) -> None:
        payload = repository_payload()
        payload["allow_merge_commit"] = True
        with self.assertRaisesRegex(verify_release_merge_policy.PolicyFailure, "merge commits"):
            verify_release_merge_policy.validate_repository_payload(payload, REPOSITORY)


# Repository settings are observed at the fixed authority; errors and context
# drift refuse. This does not change settings or qualify branch protections.
class FixedPolicyAuthorityTests(unittest.TestCase):
    def test_fixed_api_and_network_refusal(self) -> None:
        import io
        import json
        from unittest.mock import Mock, patch
        opener = Mock()
        opener.open.return_value = io.BytesIO(json.dumps(repository_payload()).encode())
        with patch.object(verify_release_merge_policy.urllib.request, "build_opener", return_value=opener):
            payload = verify_release_merge_policy.fetch_repository_payload("fixture-token")
            self.assertEqual(payload, repository_payload())
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.github.com/repos/relux-works/curator-spec")
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 30})
        opener.open.side_effect = OSError("unavailable")
        with patch.object(verify_release_merge_policy.urllib.request, "build_opener", return_value=opener):
            with self.assertRaisesRegex(verify_release_merge_policy.PolicyFailure, "could not read"):
                verify_release_merge_policy.fetch_repository_payload("fixture-token")
        with self.assertRaisesRegex(verify_release_merge_policy.PolicyFailure, "GITHUB_TOKEN"):
            verify_release_merge_policy.fetch_repository_payload("")

    def test_context_drift_refuses_before_api(self) -> None:
        import contextlib
        import io
        from unittest.mock import patch
        with patch.dict("os.environ", {"GITHUB_REPOSITORY": "other/project"}, clear=True), \
             patch("sys.argv", ["verify_release_merge_policy.py"]), \
             patch.object(verify_release_merge_policy, "fetch_repository_payload") as fetch, \
             contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(verify_release_merge_policy.main(), 1)
        self.assertIn("does not match repository policy", output.getvalue())
        fetch.assert_not_called()


class SecretFreePolicyTransportTests(SecretFreeTransportMixin, unittest.TestCase):
    failure_type = verify_release_merge_policy.PolicyFailure
    failure_message = "could not read GitHub repository settings"
    public_failure = "release merge policy verification failed: " + failure_message
    valid_output = "preserves the GitHub-verified squash fallback"
    valid_payload = staticmethod(repository_payload)

    def fetch(self, token):
        return verify_release_merge_policy.fetch_repository_payload(token)

    def invoke_main(self, token):
        import contextlib
        import io
        import os
        from unittest.mock import patch
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": token}, clear=True), \
             patch("sys.argv", ["verify_release_merge_policy.py"]), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                status = verify_release_merge_policy.main()
            except Exception as error:
                import traceback
                output.write("".join(traceback.format_exception(error)))
                status = None
        return status, output.getvalue()


if __name__ == "__main__":
    unittest.main()
