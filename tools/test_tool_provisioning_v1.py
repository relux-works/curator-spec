#!/usr/bin/env python3
"""Schema tests for tool-provisioning-v1 (agent-skill-v10, tool-receipt-v1) and launch-env-fragment-v9."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def _registry() -> Registry:
    reg = Registry()
    for path in sorted(SCHEMAS.rglob("*.schema.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        uri = doc.get("$id")
        if uri:
            reg = reg.with_resource(uri, Resource.from_contents(doc))
    return reg


def _validator(rel: str) -> Draft202012Validator:
    doc = json.loads((SCHEMAS / rel).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(doc)
    return Draft202012Validator(doc, registry=_registry())


class ToolProvisioningV1Tests(unittest.TestCase):
    def test_agent_skill_v10_valid_and_rejects_urls(self) -> None:
        v = _validator("tool-provisioning-v1/agent-skill-v10.schema.json")
        valid = {
            "schema_version": 10,
            "build_roots": ["cmd"],
            "commands": {
                "colab-glm53": {
                    "type": "build",
                    "driver": "go-v1",
                    "source_dir": "cmd/colab-glm53",
                }
            },
            "capabilities": {"network": ["colab.research.google.com"], "exec": ["colab", "ssh"]},
            "dependencies": {
                "tools": {
                    "colab": {"id": "pypi/google-colab-cli", "version": ">=0.8.0"},
                    "uv": {"id": "aqua/astral-sh/uv", "version": ">=0.10.0"},
                }
            },
        }
        v.validate(valid)

        # Reject arbitrary fetch URLs inside tool id
        bad_url = json.loads(json.dumps(valid))
        bad_url["dependencies"]["tools"]["colab"]["id"] = "https://evil.example/colab.tar.gz"
        self.assertFalse(v.is_valid(bad_url))

        # Reject extra url field on tool requirement
        bad_field = json.loads(json.dumps(valid))
        bad_field["dependencies"]["tools"]["colab"]["url"] = "https://evil.example/colab.tar.gz"
        self.assertFalse(v.is_valid(bad_field))

    def test_tool_receipt_v1(self) -> None:
        v = _validator("tool-provisioning-v1/tool-receipt-v1.schema.json")
        h = "a" * 64
        v.validate(
            {
                "schema": "curator-tool-receipt/1",
                "backend": "pypi-uv",
                "id": "pypi/google-colab-cli",
                "version": "0.8.0",
                "platform": "darwin-arm64",
                "executables": {"colab": {"relative_path": "venv/bin/colab", "sha256": h}},
                "provisioned_at": "2026-11-27T01:00:00Z",
            }
        )
        self.assertFalse(
            v.is_valid(
                {
                    "schema": "curator-tool-receipt/1",
                    "backend": "unknown",
                    "id": "pypi/google-colab-cli",
                    "version": "0.8.0",
                    "platform": "darwin-arm64",
                    "executables": {"colab": {"relative_path": "venv/bin/colab", "sha256": h}},
                    "provisioned_at": "2026-11-27T01:00:00Z",
                }
            )
        )

    def test_launch_env_fragment_v9(self) -> None:
        v = _validator("profile-command-roots-v1/launch-env-fragment-v9.schema.json")
        h = "b" * 64
        root = f"/Users/iv/.curator/environments/colab-g4-keeper/commands/{h}/darwin-arm64/bin"
        doc = {
            "fragment": "launch-env-fragment-v9",
            "environment": "claude_code",
            "profile": {"name": "colab-g4-keeper", "lock_sha256": h},
            "precedence": {"winner": "higher-weight", "placement": "winner-last"},
            "env": {"CLAUDE_CONFIG_DIR": "/Users/iv/.curator/environments/colab-g4-keeper/claude_code"},
            "permissions": {"mode": "native", "locked": False, "source": "default"},
            "command_root": {
                "lock_sha256": h,
                "plan_sha256": h,
                "generation": h,
                "platform": "darwin-arm64",
                "receipt_sha256": h,
                "marker_sha256": h,
                "inventory_sha256": h,
            },
            "path_prepend": root,
        }
        v.validate(doc)

        # Missing command_root must fail v9
        missing = dict(doc)
        del missing["command_root"]
        self.assertFalse(v.is_valid(missing))


if __name__ == "__main__":
    unittest.main()
