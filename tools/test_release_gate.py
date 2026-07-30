from __future__ import annotations

import hashlib
import json
import shutil
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
        version = "1.0.0-rc.6"
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
                "execution_policy": {
                    "portable": release_gate.PORTABLE_EXECUTION_POLICY,
                    "hardened_profile_claimed": False,
                    "hardened_profile_owner": "STORY-260728-327soo",
                    "native_control_inventory_version": (
                        release_gate.NATIVE_CONTROL_INVENTORY_VERSION
                    ),
                    "capability_evidence_record_version": (
                        release_gate.CAPABILITY_EVIDENCE_RECORD_VERSION
                    ),
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

    def test_release_surfaces_name_only_the_neutral_descriptor(self) -> None:
        version = "1.0.0-rc.6"
        schemas = self.root / "schemas" / "v1"
        schemas.mkdir(parents=True)
        (schemas / release_gate.REPOSITORY_DESCRIPTOR_SCHEMA).write_text(
            "{}\n", encoding="utf-8"
        )
        metadata_path = self.root / "release" / f"{version}.json"
        self._write_json(metadata_path, {"protocol_version": version})
        release_gate.validate_repository_descriptor(version)

        # The frozen build-source digest algorithm shares the retired stem and
        # must not trip the gate.
        (schemas / "install-marker-v2.schema.json").write_text(
            f'{{"algorithm": "{release_gate.BUILD_SOURCE_ALGORITHM_NAMESPACE}-v1"}}\n',
            encoding="utf-8",
        )
        release_gate.validate_repository_descriptor(version)

        self._write_json(
            metadata_path,
            {
                "protocol_version": version,
                "descriptor": f"{release_gate.RETIRED_DESCRIPTOR_STEM}.json",
            },
        )
        with self.assertRaisesRegex(
            release_gate.ReleaseFailure, "names the retired repository descriptor"
        ):
            release_gate.validate_repository_descriptor(version)

        self._write_json(metadata_path, {"protocol_version": version})
        (schemas / release_gate.REPOSITORY_DESCRIPTOR_SCHEMA).unlink()
        with self.assertRaisesRegex(release_gate.ReleaseFailure, "is missing"):
            release_gate.validate_repository_descriptor(version)

    def test_candidate_rejects_dishonest_execution_policy_metadata(self) -> None:
        version = "1.0.0-rc.6"
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
        base = {
            "protocol_version": version,
            "candidate_protocol_pin": {"manifest_sha256": digest},
            "downstream_consumption": {"required_manifest_sha256": digest},
            "execution_policy": {
                "portable": release_gate.PORTABLE_EXECUTION_POLICY,
                "hardened_profile_claimed": False,
                "hardened_profile_owner": "STORY-260728-327soo",
                "native_control_inventory_version": (
                    release_gate.NATIVE_CONTROL_INVENTORY_VERSION
                ),
                "capability_evidence_record_version": (
                    release_gate.CAPABILITY_EVIDENCE_RECORD_VERSION
                ),
            },
        }
        self._write_json(metadata_path, base)
        release_gate.validate_version(version)

        for label, mutation in {
            "hardened claim": {"hardened_profile_claimed": True},
            "unknown portable policy": {"portable": "hardened-worker-v1"},
            "unowned deferral": {"hardened_profile_owner": ""},
            "unpinned native-control inventory": {
                "native_control_inventory_version": None
            },
            "drifted native-control inventory": {
                "native_control_inventory_version": "rc5-native-control-inventory-v2"
            },
            "unpinned capability-evidence record": {
                "capability_evidence_record_version": None
            },
            "drifted capability-evidence record": {
                "capability_evidence_record_version": "capability-evidence-v2"
            },
            "missing policy": None,
        }.items():
            metadata = json.loads(json.dumps(base))
            if mutation is None:
                del metadata["execution_policy"]
            else:
                metadata["execution_policy"].update(mutation)
            self._write_json(metadata_path, metadata)
            with self.assertRaisesRegex(
                release_gate.ReleaseFailure,
                "does not honestly record its execution policy",
                msg=f"{label} was accepted",
            ):
                release_gate.validate_version(version)


class ProtocolRC6ReleaseGateTests(unittest.TestCase):
    VERSION = "1.0.0-rc.6"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        shutil.copytree(
            SOURCE_ROOT,
            self.root,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )
        self.root_patch = patch.object(release_gate, "ROOT", self.root)
        self.root_patch.start()

    def tearDown(self) -> None:
        self.root_patch.stop()
        self.temporary.cleanup()

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def _refresh_manifest_entry(self, relative: str) -> None:
        suite = self.root / "conformance" / "v1"
        path = suite / relative
        manifest_path = suite / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            if entry["path"] == relative:
                entry["sha256"] = (
                    "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                )
                break
        else:
            self.fail(f"manifest does not list {relative}")
        self._write_json(manifest_path, manifest)

    def test_accepts_complete_rc6_artifact_set(self) -> None:
        release_gate.validate_protocol_artifacts(self.VERSION)

    def test_rejects_each_missing_required_artifact(self) -> None:
        for relative in sorted(release_gate.RC6_REQUIRED_FILES):
            with self.subTest(path=relative):
                path = self.root / relative
                payload = path.read_bytes()
                path.unlink()
                try:
                    with self.assertRaises(release_gate.ReleaseFailure):
                        release_gate.validate_protocol_artifacts(self.VERSION)
                finally:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(payload)

    def test_rejects_renamed_v6_schema(self) -> None:
        source = self.root / "schemas" / "v1" / "agent-skill-v6.schema.json"
        source.rename(source.with_name("agent-skill-v6-renamed.schema.json"))
        with self.assertRaisesRegex(
            release_gate.ReleaseFailure, "required artifacts are missing"
        ):
            release_gate.validate_protocol_artifacts(self.VERSION)

    def test_rejects_missing_required_manifest_entry(self) -> None:
        manifest_path = self.root / "conformance" / "v1" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"] = [
            entry
            for entry in manifest["files"]
            if entry["path"] != "vectors/manager-lifecycle.json"
        ]
        self._write_json(manifest_path, manifest)
        with self.assertRaises(release_gate.ReleaseFailure):
            release_gate.validate_protocol_artifacts(self.VERSION)

    def test_rejects_removed_lifecycle_case_with_updated_manifest_hash(self) -> None:
        relative = "vectors/manager-lifecycle.json"
        path = self.root / "conformance" / "v1" / relative
        vector = json.loads(path.read_text(encoding="utf-8"))
        vector["recovery_cases"] = [
            case
            for case in vector["recovery_cases"]
            if case["name"]
            != "interrupted-global-journal-recovered-by-transaction-id"
        ]
        self._write_json(path, vector)
        self._refresh_manifest_entry(relative)
        with self.assertRaisesRegex(release_gate.ReleaseFailure, "lifecycle"):
            release_gate.validate_protocol_artifacts(self.VERSION)

    def test_rejects_stale_compiled_fixture_with_updated_manifest_hash(self) -> None:
        relative = "vectors/manager-lifecycle.json"
        path = self.root / "conformance" / "v1" / relative
        vector = json.loads(path.read_text(encoding="utf-8"))
        vector["compiled_build_fixture"]["execution_policy"] = "hardened-worker-v1"
        self._write_json(path, vector)
        self._refresh_manifest_entry(relative)
        with self.assertRaisesRegex(release_gate.ReleaseFailure, "lifecycle"):
            release_gate.validate_protocol_artifacts(self.VERSION)

    def test_rejects_redefined_claim_v1_and_v2_history(self) -> None:
        for schema_name, protocol_version in (
            ("conformance-claim-v1.schema.json", self.VERSION),
            ("conformance-claim-v2.schema.json", self.VERSION),
        ):
            with self.subTest(schema=schema_name):
                path = self.root / "schemas" / "v1" / schema_name
                payload = path.read_bytes()
                schema = json.loads(payload)
                schema["properties"]["protocol_version"]["const"] = protocol_version
                self._write_json(path, schema)
                try:
                    with self.assertRaises(release_gate.ReleaseFailure):
                        release_gate.validate_protocol_artifacts(self.VERSION)
                finally:
                    path.write_bytes(payload)

    def test_rejects_claim_v3_transition_mismatch(self) -> None:
        path = self.root / "schemas" / "v1" / "conformance-claim-v3.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema["properties"]["protocol_version"]["const"] = self.VERSION
        self._write_json(path, schema)
        with self.assertRaises(release_gate.ReleaseFailure):
            release_gate.validate_protocol_artifacts(self.VERSION)

    def test_rejects_changed_published_rc5_release_metadata(self) -> None:
        path = self.root / "release" / "1.0.0-rc.5.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["created_at"] = "2026-07-30T00:00:00Z"
        self._write_json(path, metadata)
        with self.assertRaisesRegex(
            release_gate.ReleaseFailure, "published rc.5 release metadata changed"
        ):
            release_gate.validate_protocol_artifacts(self.VERSION)

    def test_rejects_rc6_history_rewriting_rc5_identity(self) -> None:
        path = self.root / "release" / f"{self.VERSION}.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["historical_release"]["metadata_sha256"] = "sha256:" + "0" * 64
        self._write_json(path, metadata)
        with self.assertRaisesRegex(
            release_gate.ReleaseFailure,
            "rewrites rc.5 evidence or fabricates an rc.6 claim",
        ):
            release_gate.validate_protocol_artifacts(self.VERSION)

    def test_rc6_has_no_conformance_claim_schema(self) -> None:
        path = self.root / "claim.json"
        self._write_json(path, {})
        with self.assertRaisesRegex(
            release_gate.ReleaseFailure,
            "claim verification is not defined for 1.0.0-rc.6",
        ):
            release_gate.validate_conformance_claim(path, self.VERSION)

    def test_rejects_stale_rc6_suite_pin(self) -> None:
        path = self.root / "release" / f"{self.VERSION}.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["candidate_protocol_pin"]["manifest_sha256"] = (
            "sha256:" + "0" * 64
        )
        self._write_json(path, metadata)
        with self.assertRaisesRegex(
            release_gate.ReleaseFailure, "does not pin the exact suite manifest"
        ):
            release_gate.validate_version(self.VERSION)

    def test_rejects_duplicate_rc6_suite_pin(self) -> None:
        path = self.root / "release" / f"{self.VERSION}.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        expected = metadata["candidate_protocol_pin"]["manifest_sha256"]
        payload = path.read_text(encoding="utf-8").replace(
            f'"manifest_sha256": "{expected}"',
            (
                f'"manifest_sha256": "{expected}",\n'
                f'    "manifest_sha256": "sha256:{"0" * 64}"'
            ),
            1,
        )
        path.write_text(payload, encoding="utf-8")
        with self.assertRaisesRegex(release_gate.ReleaseFailure, "duplicate JSON key"):
            release_gate.validate_version(self.VERSION)


if __name__ == "__main__":
    unittest.main()
