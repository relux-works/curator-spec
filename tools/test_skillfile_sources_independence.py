from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).with_name("verify_skillfile_sources_independence.py")
CONDITIONAL_CLAUSE = (
    "Machine-global Skillfiles follow [environments §9.4 profile locks]"
    "(environments.md#94-profile-scoped-skills-and-migration) when the manager "
    "implements that capability."
)


class SkillfileSourcesIndependenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._write(
            "schemas/v1/common.schema.json",
            '{"$defs":{"stable":{"type":"string"}}}\n',
        )
        self._write(
            "schemas/skillfile-sources-v1/skillfile.schema.json",
            json.dumps({"properties": {"name": {"$ref": "../v1/common.schema.json#/$defs/stable"}}}) + "\n",
        )
        self._write("protocol/core.md", "# Core\n\n## 3. Packages\n\n## 5. Sources\n\n## 6. Snapshots\n")
        self._write("protocol/registry.md", "# Registry\n\n## 3. Audit records\n")
        self._write("profiles/manager.md", "# Manager\n\n## 2.1 Read-only planning\n\n## 11. External repositories\n")
        self._write(
            "protocol/skillfile-sources.md",
            "The manager section 2.1 follows core section 3.\n",
        )
        self._write(
            "protocol/repository-transport.md",
            "Registry §3 and core sections 5–6 apply.\n",
        )
        self._git("init", "-q")
        self._git("config", "user.name", "Gate Test")
        self._git("config", "user.email", "gate-test@example.invalid")
        self._git("config", "commit.gpgsign", "false")
        self._git("add", ".")
        self._git("commit", "-qm", "rc.10 baseline")
        self._git("tag", "v1.0.0-rc.10")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            self.fail(f"git {' '.join(args)} failed: {result.stderr}")
        return result

    def _run_gate(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(GATE), "--root", str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_candidate_passes_through_the_gate_entry_point(self) -> None:
        result = self._run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1/1 byte-identical", result.stdout)
        self.assertIn("Skillfile source independence gate passed", result.stdout)

    def test_reference_to_rc12_only_v1_definition_fails_through_the_gate(self) -> None:
        # This v1 schema was added after rc.10 and is present in rc.12.
        self._write(
            "schemas/v1/agent-context-v1.schema.json",
            '{"$defs":{"context":{"type":"object"}}}\n',
        )
        self._write(
            "schemas/skillfile-sources-v1/skillfile.schema.json",
            json.dumps({"properties": {"context": {"$ref": "../v1/agent-context-v1.schema.json#/$defs/context"}}})
            + "\n",
        )

        result = self._run_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("cannot read schemas/v1/agent-context-v1.schema.json at v1.0.0-rc.10", result.stderr)

    def test_changed_definition_bytes_fail_even_when_json_remains_valid(self) -> None:
        self._write(
            "schemas/v1/common.schema.json",
            '{\n  "$defs": {\n    "stable": {\n      "type": "string"\n    }\n  }\n}\n',
        )

        result = self._run_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("definition differs from v1.0.0-rc.10", result.stderr)

    def test_rc12_only_manager_clause_citation_fails_through_the_gate(self) -> None:
        self._write(
            "profiles/manager.md",
            "# Manager\n\n## 2.1 Read-only planning\n\n## 11. External repositories\n\n## 12. Agent environments\n\n### 12.1 Environment adapters\n",
        )
        self._write(
            "protocol/skillfile-sources.md",
            "The manager section 2.1 follows core section 3. The manager section 12.1 is required.\n",
        )

        result = self._run_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("manager section 12.1 is not present at v1.0.0-rc.10", result.stderr)

    def test_exact_conditional_capability_clause_is_allowlisted(self) -> None:
        self._write(
            "protocol/skillfile-sources.md",
            f"{CONDITIONAL_CLAUSE}\n",
        )

        result = self._run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 exact conditional exception(s) allowlisted", result.stdout)
        self.assertIn("optional machine-global profile-lock capability", result.stdout)

    def test_same_post_rc10_citation_without_condition_fails(self) -> None:
        unconditioned = CONDITIONAL_CLAUSE.removesuffix(" when the manager implements that capability.") + "."
        self._write("protocol/skillfile-sources.md", f"{unconditioned}\n")

        result = self._run_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("environments section 9.4 is not present at v1.0.0-rc.10", result.stderr)

    def test_informative_only_marker_does_not_allow_other_post_rc10_citation(self) -> None:
        self._write(
            "profiles/manager.md",
            "# Manager\n\n## 2.1 Read-only planning\n\n## 11. External repositories\n\n## 12. Agent environments\n\n### 12.1 Environment adapters\n",
        )
        self._write(
            "protocol/repository-transport.md",
            "Informative-only manager section 12.1 is mentioned here.\n",
        )

        result = self._run_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("manager section 12.1 is not present at v1.0.0-rc.10", result.stderr)

    def test_exact_conditional_clause_is_not_allowlisted_in_another_file(self) -> None:
        self._write("protocol/repository-transport.md", f"{CONDITIONAL_CLAUSE}\n")

        result = self._run_gate()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("environments section 9.4 is not present at v1.0.0-rc.10", result.stderr)


if __name__ == "__main__":
    unittest.main()
