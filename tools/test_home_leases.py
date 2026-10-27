"""Specification checks; these tests execute no Curator or launcher runtime."""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

import home_leases

ROOT = Path(__file__).resolve().parents[1]


class HomeLeaseSpecificationTests(unittest.TestCase):
    # The published corpus validates both sides of each shape pair and covers every HL/W identifier.
    def test_published_pairs(self) -> None:
        schemas, semantic = home_leases.check_corpus(ROOT)
        self.assertGreaterEqual(schemas, 109)
        self.assertGreaterEqual(semantic, 42)

    # Controls prove this checker rejects a planted accepted negative and missing positive, not runtime guard behavior.
    def test_checker_detects_control_plants(self) -> None:
        checks = home_leases.validators(ROOT)
        corpus = home_leases.decode((ROOT / "conformance/home-leases-v1/schema-cases.json").read_bytes())
        pair = copy.deepcopy(corpus["pairs"][0])
        home_leases.check_schema_pairs([pair], checks)
        pair["negative"] = pair["positive"]
        with self.assertRaisesRegex(ValueError, "negative accepted"):
            home_leases.check_schema_pairs([pair], checks)
        cases = home_leases.decode((ROOT / "conformance/home-leases-v1/cases.json").read_bytes())["cases"]
        control = copy.deepcopy(cases[0])
        home_leases.check_semantic_pairs([control], {control["requirement"]})
        del control["positive"]
        with self.assertRaisesRegex(ValueError, "requires negative and positive"):
            home_leases.check_semantic_pairs([control], {control["requirement"]})

    # Dropping an obligation is detected independently of whether remaining examples are valid.
    def test_missing_requirement_is_detected(self) -> None:
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            home_leases.check_semantic_pairs([], {"HL03"})


if __name__ == "__main__":
    unittest.main()
