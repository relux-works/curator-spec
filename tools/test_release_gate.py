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
        version = "1.0.0-rc.5"
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


class ToolchainSurfaceReleaseGateTests(unittest.TestCase):
    """The wire-surface, registry and guidance gates as release properties.

    They also run under ``make validate``. Running them again at release time is
    deliberate: the wire-surface enumeration cannot be a runtime diagnostic,
    because a field that does not exist produces no value to diagnose, so the
    release is the last point at which a published property name can still be
    refused.
    """

    def test_the_shipped_release_surface_passes(self) -> None:
        release_gate.validate_toolchain_surface()

    def test_every_named_slot_is_shipped(self) -> None:
        for slot in release_gate.TOOLCHAIN_SCHEMA_SLOTS:
            with self.subTest(slot=slot):
                self.assertTrue((SOURCE_ROOT / "schemas" / "v1" / slot).is_file())

    def test_a_missing_slot_fails_the_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "schemas" / "v1").mkdir(parents=True)
            (root / "conformance" / "next" / "vectors").mkdir(parents=True)
            for name in ("common.schema.json",):
                (root / "schemas" / "v1" / name).write_bytes(
                    (SOURCE_ROOT / "schemas" / "v1" / name).read_bytes()
                )
            for name in ("toolchain-registry.json", "toolchain-guidance-catalog.json"):
                (root / "conformance" / "next" / "vectors" / name).write_bytes(
                    (SOURCE_ROOT / "conformance" / "next" / "vectors" / name).read_bytes()
                )
            for name in release_gate.toolchain_gate.TOOLCHAIN_VECTOR_FILES:
                target = root / "conformance" / "next" / "vectors" / name
                if not target.exists():
                    target.write_bytes(
                        (SOURCE_ROOT / "conformance" / "next" / "vectors" / name).read_bytes()
                    )
            (root / "tools" / "toolchain-boundary-probe").mkdir(parents=True)
            (root / "tools" / "toolchain-boundary-probe" / "main.go").write_bytes(
                (SOURCE_ROOT / "tools" / "toolchain-boundary-probe" / "main.go").read_bytes()
            )
            with patch.object(release_gate, "ROOT", root):
                with self.assertRaises(release_gate.ReleaseFailure) as raised:
                    release_gate.validate_toolchain_surface()
                self.assertIn("release is missing", str(raised.exception))

    def test_a_resolution_input_property_fails_the_release(self) -> None:
        common = json.loads(
            (SOURCE_ROOT / "schemas" / "v1" / "common.schema.json").read_text(encoding="utf-8")
        )
        common["$defs"]["skillBuildTargetV2"]["properties"]["toolchain_root"] = {
            "type": "string"
        }
        with self.assertRaises(release_gate.ReleaseFailure) as raised:
            release_gate.toolchain_gate.check_wire_surface(
                common, release_gate.ReleaseFailure
            )
        self.assertIn("names a resolution input", str(raised.exception))


class FrozenReleaseGateTests(unittest.TestCase):
    """A release may not reach a tag having rewritten an accepted predecessor."""

    ARTIFACTS = (
        "release/frozen.json",
        "release/1.0.0-rc.5.json",
        "conformance/v1/manifest.json",
        "conformance/v1/schema-cases/index.json",
    )

    def _root(self) -> Path:
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for relative in self.ARTIFACTS:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((SOURCE_ROOT / relative).read_bytes())
        self.enterContext(patch.object(release_gate, "ROOT", root))
        return root

    def test_the_shipped_repository_passes(self) -> None:
        self._root()
        release_gate.validate_frozen_releases("1.0.0-rc.5")

    def test_a_rewritten_suite_manifest_fails_the_release(self) -> None:
        root = self._root()
        path = root / "conformance" / "v1" / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["files"].append({"path": "vectors/x.json", "sha256": "sha256:" + "0" * 64})
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with self.assertRaises(release_gate.ReleaseFailure) as raised:
            release_gate.validate_frozen_releases("1.0.0-rc.5")
        self.assertIn("was rewritten", str(raised.exception))

    def test_a_regenerated_pair_that_agrees_with_itself_still_fails(self) -> None:
        root = self._root()
        manifest_path = root / "conformance" / "v1" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"].append({"path": "vectors/x.json", "sha256": "sha256:" + "0" * 64})
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        digest = "sha256:" + hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        document_path = root / "release" / "1.0.0-rc.5.json"
        document = json.loads(document_path.read_text(encoding="utf-8"))
        document["candidate_protocol_pin"]["manifest_sha256"] = digest
        document["downstream_consumption"]["required_manifest_sha256"] = digest
        document_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        with self.assertRaises(release_gate.ReleaseFailure) as raised:
            release_gate.validate_frozen_releases("1.0.0-rc.5")
        self.assertIn("was rewritten", str(raised.exception))

    def test_a_release_document_without_a_frozen_record_fails(self) -> None:
        root = self._root()
        (root / "release" / "1.0.0-rc.9.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaises(release_gate.ReleaseFailure) as raised:
            release_gate.validate_frozen_releases("1.0.0-rc.9")
        self.assertIn("does not record the 1.0.0-rc.9 release identity", str(raised.exception))

    def test_a_stable_version_without_a_release_document_is_not_required_to_be_recorded(
        self,
    ) -> None:
        self._root()
        release_gate.validate_frozen_releases("1.0.0")


if __name__ == "__main__":
    unittest.main()
