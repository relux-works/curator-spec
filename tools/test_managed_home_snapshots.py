from __future__ import annotations

import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import managed_home_snapshots as snapshots
from test_validate import validate


class SnapshotContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = validate.ROOT / "conformance" / snapshots.NAMESPACE
        cls.checks = snapshots.validators(validate.ROOT, validate.load_json)

    def setUp(self):
        self.manifest = validate.load_json(self.suite / "golden/manifest.json")
        self.launch = validate.load_json(self.suite / "golden/launch.json")
        vector = validate.load_json(self.suite / "vectors.json")
        self.content = {entry["path"]: ((self.suite / entry["source"]).read_bytes(), entry["mode"])
                        for entry in vector["cases"][0]["content"]}

    def check(self, **kwargs):
        return snapshots.check_bundle(self.manifest, self.launch, self.content,
                                      self.checks, validate.ccj1_bytes,
                                      validate.validate_wire_semantics, **kwargs)

    def rebind_launch(self):
        self.manifest["launch_sha256"] = snapshots.sha256(validate.ccj1_bytes(self.launch) + b"\n")

    # The metadata corpus and all pins are consumed by the ordinary validator.
    # This proves corpus consistency, not any real materialize operation.
    def test_corpus_is_valid(self):
        with contextlib.redirect_stdout(io.StringIO()):
            validate.validate_managed_home_snapshots()

    # Same portable output from a different source binding differs on disk;
    # producer version, adapter, profile, descriptor and inventory still bind.
    def test_source_binding_is_not_portable_identity(self):
        self.check()
        other = copy.deepcopy(self.manifest)
        other["fragment_sha256"] = "f" * 64
        self.assertNotEqual(validate.ccj1_bytes(other), validate.ccj1_bytes(self.manifest))
        self.assertEqual(snapshots.portable_projection(other), snapshots.portable_projection(self.manifest))
        for field, value in [("curator_version", "2.0.0"), ("adapter", "pi"),
                             ("profile", {"name": "other", "lock_sha256": "0" * 64}),
                             ("launch_sha256", "e" * 64), ("files", [])]:
            other = copy.deepcopy(self.manifest)
            other[field] = value
            with self.subTest(field=field):
                self.assertNotEqual(snapshots.portable_projection(other),
                                    snapshots.portable_projection(self.manifest))

    # Independent extra/missing entries are rejected, including a nested file;
    # a root-context-only inventory cannot stand in for the complete closure.
    def test_complete_entry_set(self):
        self.check()
        for path in ("home/extra", "home/skills/sample/extra"):
            self.content[path] = (b"extra", "0600")
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "^entry-set$"):
                self.check()
            del self.content[path]
        del self.content["home/skills/sample/SKILL.md"]
        with self.assertRaisesRegex(ValueError, "^entry-set$"):
            self.check()

    # Execute metadata is semantic identity even when payload bytes match.
    def test_execute_mode_binds_identity(self):
        self.check()
        path = "home/skills/sample/run.sh"
        self.content[path] = (self.content[path][0], "0600")
        with self.assertRaisesRegex(ValueError, "^file-identity$"):
            self.check()

    # Size and raw bytes are checked independently, not just a stored hash.
    def test_file_bytes_and_size(self):
        self.check()
        path = "home/AGENTS.md"
        original = self.content[path]
        self.content[path] = (b"x" * len(original[0]), original[1])
        with self.assertRaisesRegex(ValueError, "^file-identity$"):
            self.check()
        self.content[path] = original
        next(entry for entry in self.manifest["files"] if entry["path"] == path)["size"] += 1
        with self.assertRaisesRegex(ValueError, "^file-identity$"):
            self.check()

    # Case/normalization aliases, including directory-only aliases, duplicate
    # paths and file ancestors reject before bytes can authorize an entry.
    def test_path_aliases_and_ancestors(self):
        self.check()
        # Isolate path admission: absent channel references must not mask a
        # narrowed alias/ancestor gate with an unrelated later refusal.
        self.launch.pop("system_prompt")
        self.launch.pop("mcp")
        self.rebind_launch()
        cases = [("path-collision", ["home/A", "home/a"]),
                 ("path-collision", ["home/Skills/a", "home/skills/b"]),
                 ("path-collision", ["home/e\u0301", "home/é"]),
                 ("path-collision", ["home/a", "home/a"]),
                 ("file-ancestor", ["home/a", "home/a/b"])]
        original = copy.deepcopy(self.manifest["files"][0])
        payload = self.content[original["path"]]
        for expected, paths in cases:
            self.manifest["files"] = [dict(original, path=path) for path in sorted(paths)]
            self.content = {path: payload for path in paths}
            with self.subTest(paths=paths), self.assertRaisesRegex(ValueError, "^" + expected + "$"):
                self.check()

    # Relative traversal and absolute/drive/UNC spellings never satisfy the
    # file grammar; ordinary home-relative paths remain a positive control.
    def test_schema_path_boundary(self):
        self.check()
        original = self.manifest["files"][0]["path"]
        for path in ("home/../escape", "home/./file", "home//file", "/file", "C:/file",
                     "//share/file", "home/a\\b", "other/file", "home/a\0b"):
            self.manifest["files"][0]["path"] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "^manifest-schema$"):
                self.check()
        self.manifest["files"][0]["path"] = original
        self.check()

    # Channel paths must exist in the inventory; selecting an arbitrary valid
    # channel shape cannot replace the adapter's exact MCP/system semantics.
    def test_channels_require_inventory_and_adapter_semantics(self):
        self.check()
        original = copy.deepcopy(self.launch)
        self.launch["mcp"]["path"] = "home/absent"
        self.rebind_launch()
        with self.assertRaisesRegex(ValueError, "^channel-reference$"):
            self.check()
        self.launch = original
        self.launch["mcp"]["channels"][0]["name"] = "other"
        self.rebind_launch()
        with self.assertRaisesRegex(ValueError, "^channel-semantics$"):
            self.check()

    # Declared adapter and profile/lock cannot disagree across metadata files.
    def test_adapter_profile_binding(self):
        self.check()
        for field, value in [("adapter", "pi"), ("profile", {"name": "sample", "lock_sha256": "f" * 64})]:
            original = self.manifest[field]
            self.manifest[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "^adapter-profile$"):
                self.check()
            self.manifest[field] = original

    # The presentation LF is part of launch/manifest byte identity; neither
    # missing nor additional LF is the frozen canonical disk representation.
    def test_metadata_framing_and_launch_digest(self):
        self.check()
        for field, doc in [("manifest_bytes", self.manifest), ("launch_bytes", self.launch)]:
            raw = validate.ccj1_bytes(doc)
            for payload in (raw, raw + b"\n\n", b" " + raw + b"\n"):
                with self.subTest(field=field, payload=payload[:1]), self.assertRaisesRegex(ValueError, "^metadata-canonical$"):
                    self.check(**{field: payload})
        self.manifest["launch_sha256"] = snapshots.sha256(validate.ccj1_bytes(self.launch))
        with self.assertRaisesRegex(ValueError, "^launch-digest$"):
            self.check()

    # New wire objects stay closed; old fragment fields, extra env names and
    # unsupported path-prepend are not silently admitted by the descriptor.
    def test_closed_shapes_and_env_maps(self):
        self.check()
        for key, value in [("extra", True), ("fragment", "launch-env-fragment-v3"),
                           ("path_prepend", "home/bin"), ("root_context", {"exclusive": True})]:
            self.launch[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "^launch-schema$"):
                self.check()
            del self.launch[key]
        self.launch["env"]["HOME"] = "home"
        with self.assertRaisesRegex(ValueError, "^launch-schema$"):
            self.check()

    # Manifest structure rejects extra members at every closed level and
    # negative, fractional or unsafe sizes; zero size is structurally valid.
    def test_manifest_closed_shape_and_size_domain(self):
        self.check()
        for target in (self.manifest, self.manifest["profile"], self.manifest["files"][0]):
            target["extra"] = True
            with self.assertRaisesRegex(ValueError, "^manifest-schema$"):
                self.check()
            del target["extra"]
        for size in (-1, 1.5, 9_007_199_254_740_992):
            self.manifest["files"][0]["size"] = size
            with self.subTest(size=size), self.assertRaisesRegex(ValueError, "^manifest-schema$"):
                self.check()
        self.manifest["files"][0]["size"] = 0
        self.assertTrue(self.checks[snapshots.MANIFEST_SCHEMA].is_valid(self.manifest))

    # The Muse root fact is tied to selected content; absent content has no
    # fact. This validates fixture correspondence, not native discovery.
    def test_muse_fact_correspondence(self):
        self.launch.update(environment="muse", env={
            "XDG_CONFIG_HOME": "home/config", "XDG_DATA_HOME": "home/data",
            "XDG_STATE_HOME": "home/state", "XDG_CACHE_HOME": "home/cache"})
        self.launch.pop("mcp")
        self.launch.pop("system_prompt")
        self.manifest["adapter"] = "muse"
        self.manifest["files"] = []
        self.content = {}
        self.rebind_launch()
        self.check()
        payload = b"Use the declared instructions.\n"
        self.content["home/config/muse/AGENTS.md"] = (payload, "0600")
        self.manifest["files"] = [{"path": "home/config/muse/AGENTS.md", "size": len(payload),
                                   "sha256": snapshots.sha256(payload), "mode": "0600"}]
        with self.assertRaisesRegex(ValueError, "^root-context$"):
            self.check()
        self.launch["root_context"] = {"exclusive": True}
        self.rebind_launch()
        self.check()
        self.manifest["files"] = []
        self.content = {}
        with self.assertRaisesRegex(ValueError, "^root-context$"):
            self.check()

    # Duplicate JSON members are a read failure, not a valid last-wins object.
    def test_duplicate_json_is_not_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"snapshot":"managed-home-snapshot-v1","snapshot":"other"}')
            with self.assertRaisesRegex(validate.ValidationFailure, "duplicate JSON key"):
                validate.load_json(path)

    # A corrupted semantic verdict fails through the production corpus checker.
    def test_semantic_verdict_cannot_be_self_minted(self):
        vector = validate.load_json(self.suite / "vectors.json")
        case = next(case for case in vector["cases"] if case["name"] == "extra-entry")
        case["expected"] = "accept"
        with self.assertRaisesRegex(ValueError, "extra-entry: expected accept, got entry-set"):
            snapshots.check_corpus(validate.ROOT, validate.load_json, validate.ccj1_bytes,
                                   validate.validate_wire_semantics, vector)

    # Main must actually dispatch the snapshot checker; an isolated planted
    # corpus failure has to produce exit 1 with its intended diagnostic.
    def test_validator_dispatch_detects_snapshot_failure(self):
        with contextlib.ExitStack() as stack:
            for name in vars(validate):
                if name.startswith("validate_") and name not in {"validate_managed_home_snapshots", "validate_wire_semantics"}:
                    stack.enter_context(patch.object(validate, name, return_value=None))
            stack.enter_context(patch.object(snapshots, "check_corpus", side_effect=ValueError("snapshot-control")))
            stderr = io.StringIO()
            stack.enter_context(contextlib.redirect_stderr(stderr))
            self.assertEqual(validate.main(), 1)
            self.assertIn("managed-home snapshots: snapshot-control", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
