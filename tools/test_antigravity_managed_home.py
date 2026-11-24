"""Unit tests for CIP-0033 Antigravity managed-home schemas and conformance suite."""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import antigravity_managed_home  # noqa: E402

ROOT = TOOLS_DIR.parent


class AntigravityManagedHomeTest(unittest.TestCase):
    def test_conformance_cases_pass(self) -> None:
        buf = io.StringIO()
        rc = antigravity_managed_home.run(ROOT, buf)
        self.assertEqual(rc, 0, buf.getvalue())
        self.assertIn("antigravity-managed-home-v1:", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
