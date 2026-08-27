from __future__ import annotations

import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import release_gate


SOURCE_ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"


class StableReleaseGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self._git("init", "-q")
        self._git("config", "user.name", "Release Gate Test")
        self._git("config", "user.email", "release-gate@example.invalid")
        (self.root / "conformance" / "v1").mkdir(parents=True)
        (self.root / "reviews").mkdir()
        (self.root / "README.md").write_text(f"**Version:** {VERSION}\n", encoding="utf-8")
        (self.root / "CHANGELOG.md").write_text(f"## {VERSION}\n", encoding="utf-8")
        self._write_json(
            self.root / "conformance" / "v1" / "manifest.json",
            {"protocol_version": VERSION, "files": []},
        )
        (self.root / "reviews" / "review-report-v2.schema.json").write_bytes(
            (SOURCE_ROOT / "reviews" / "review-report-v2.schema.json").read_bytes()
        )
        self._commit("Freeze stable candidate")
        self.candidate = self._git("rev-parse", "HEAD")
        self.root_patch = patch.object(release_gate, "ROOT", self.root)
        self.root_patch.start()

    def tearDown(self) -> None:
        self.root_patch.stop()
        self.temporary.cleanup()

    def _git(self, *arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def _commit(self, message: str) -> None:
        self._git("add", ".")
        self._git("-c", "commit.gpgsign=false", "commit", "-q", "-m", message)

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def _report(self, review_type: str, contact: str) -> dict[str, object]:
        return {
            "schema_version": 2,
            "protocol_version": VERSION,
            "review_type": review_type,
            "reviewed_commit": self.candidate,
            "reviewer": {
                "name": f"{review_type.title()} Reviewer",
                "affiliation": "Independent Review Lab",
                "contact": contact,
                "independent": True,
                "project_maintainer": False,
                "authored_reviewed_changes": False,
                "conflicts": "No conflicts identified.",
            },
            "scope": ["protocol/registry.md", "profiles/registry-service.md"],
            "completed_at": "2026-07-13T00:00:00Z",
            "source_url": f"https://example.invalid/{review_type}",
            "conclusion": "pass",
            "findings": [],
        }

    def _commit_reports(self, security_contact: str, interoperability_contact: str) -> str:
        review_root = self.root / "reviews" / VERSION
        self._write_json(review_root / "security.json", self._report("security", security_contact))
        self._write_json(
            review_root / "interoperability.json",
            self._report("interoperability", interoperability_contact),
        )
        self._commit("Publish independent reviews")
        return self._git("rev-parse", "HEAD")

    def test_accepts_distinct_independent_reviewers_on_frozen_candidate(self) -> None:
        release_commit = self._commit_reports(
            "security@example.invalid",
            "interop@example.invalid",
        )
        release_gate.validate_checkout(release_commit)
        release_gate.validate_version(VERSION)
        release_gate.validate_reviews(VERSION, release_commit)

    def test_rejects_same_reviewer_contact_case_insensitively(self) -> None:
        release_commit = self._commit_reports(
            "Reviewer@Example.invalid",
            " reviewer@example.invalid ",
        )
        with self.assertRaisesRegex(release_gate.ReleaseFailure, "different reviewer contacts"):
            release_gate.validate_reviews(VERSION, release_commit)

    def test_rejects_normative_change_after_reviewed_commit(self) -> None:
        self._commit_reports(
            "security@example.invalid",
            "interop@example.invalid",
        )
        (self.root / "README.md").write_text(
            f"**Version:** {VERSION}\nNormative drift.\n",
            encoding="utf-8",
        )
        self._commit("Change candidate after review")
        release_commit = self._git("rev-parse", "HEAD")
        with self.assertRaisesRegex(release_gate.ReleaseFailure, "normative files changed"):
            release_gate.validate_reviews(VERSION, release_commit)

    def test_candidate_requires_exact_suite_manifest_pin(self) -> None:
        version = "1.0.0-rc.5"
        (self.root / "README.md").write_text(
            f"**Version:** {version}\n", encoding="utf-8"
        )
        (self.root / "CHANGELOG.md").write_text(
            f"## {version}\n", encoding="utf-8"
        )
        manifest_path = self.root / "conformance" / "v1" / "manifest.json"
        self._write_json(
            manifest_path, {"protocol_version": version, "files": []}
        )
        digest = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        metadata_path = self.root / "release" / f"{version}.json"
        self._write_json(
            metadata_path,
            {
                "protocol_version": version,
                "candidate_protocol_pin": {"manifest_sha256": digest},
                "downstream_consumption": {
                    "required_manifest_sha256": digest,
                },
            },
        )
        release_gate.validate_version(version)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["downstream_consumption"]["required_manifest_sha256"] = (
            "sha256:" + "0" * 64
        )
        self._write_json(metadata_path, metadata)
        with self.assertRaisesRegex(
            release_gate.ReleaseFailure, "does not pin the exact suite manifest"
        ):
            release_gate.validate_version(version)


if __name__ == "__main__":
    unittest.main()
