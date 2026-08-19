from __future__ import annotations

import unittest

import verify_release_merge_policy


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


if __name__ == "__main__":
    unittest.main()
