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


if __name__ == "__main__":
    unittest.main()
