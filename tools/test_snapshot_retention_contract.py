"""Pin the recovery boundary of the retention dry-run contract."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SnapshotRetentionRecoveryContractTests(unittest.TestCase):
    def test_manager_requires_read_only_recovery_inspection(self):
        text = (ROOT / "profiles/manager.md").read_text()
        execution = text.split("### 10.1 Snapshot-cache retention", 1)[1].split("**Execution.**", 1)[1].split("**Retention report.**", 1)[0]
        self.assertIn("A dry run MUST NOT execute\ntransaction recovery or cleanup that could delete state", execution)
        self.assertIn("MUST refuse before computing a retention plan", execution)
        self.assertIn("exit 1", execution)
        self.assertIn("transaction targets and interrupted-removal leftovers", execution)
        self.assertIn("real run over a certain reference\nset", execution)

    def test_cli_documents_refusal_and_no_deletion_boundary(self):
        text = (ROOT / "cli/curator.md").read_text()
        self.assertIn("`cache prune --dry-run` never executes deleting transaction recovery", text)
        self.assertIn("refuses before computing the plan, removes nothing, and\nexits 1", text)
        self.assertIn("promise includes transaction targets and interrupted-removal leftovers", text)
