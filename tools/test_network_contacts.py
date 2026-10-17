"""Executable specification checks; no manager runtime is qualified here."""

import copy
import unittest
from unittest.mock import patch

import network_contacts as contacts


class NetworkContactTests(unittest.TestCase):
    # Each subtest recomputes findings from URL fixture bytes against authored outcomes.
    def test_network_contact_vectors(self):
        vector = contacts.load_vectors()
        for case in vector["cases"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(contacts.evaluate(case), case["expected"])

    # The public repository checker must consume all cases, including required negatives.
    def test_repository_checker_consumes_corpus(self):
        self.assertGreater(contacts.validate(), 0)

    def test_missing_case_is_rejected(self):
        vector = contacts.load_vectors()
        vector["cases"] = vector["cases"][1:]
        with self.assertRaisesRegex(ValueError, "case inventory"):
            contacts.validate(vector)

    # A forged clean result for a mixed file must fail, with the real host named.
    def test_mixed_file_finding_cannot_be_dropped(self):
        vector = copy.deepcopy(contacts.load_vectors())
        case = next(c for c in vector["cases"] if c["name"] == "mixed-reserved-first")
        case["expected"]["findings"] = []
        case["expected"]["capability_check_passes"] = True
        with self.assertRaisesRegex(ValueError, "mixed-reserved-first.*api.example.com"):
            contacts.validate(vector)

    # These controls narrow the exemption boundary while leaving the audit present.
    def test_example_com_exemption_mutant_is_killed(self):
        original = contacts.is_network_contact
        with patch.object(contacts, "is_network_contact", side_effect=lambda host: (
            False if contacts.normalize_host(host) == "example.com" else original(host)
        )):
            with self.assertRaisesRegex(ValueError, "documentation-com.*example.com"):
                contacts.validate()

    def test_substring_exemption_mutant_is_killed(self):
        original = contacts.is_network_contact
        with patch.object(contacts, "is_network_contact", side_effect=lambda host: (
            False if "test" in contacts.normalize_host(host) else original(host)
        )):
            with self.assertRaisesRegex(ValueError, "lookalike-nested-test.*x.test.evil.com"):
                contacts.validate()

    # Exemption applies to a host, never the remaining hosts in a file.
    def test_mixed_file_preserves_real_host_in_both_orders(self):
        cases = {c["name"]: c for c in contacts.load_vectors()["cases"]}
        for name in ("mixed-reserved-first", "mixed-real-first"):
            with self.subTest(case=name):
                result = contacts.evaluate(cases[name])
                self.assertEqual([f["host"] for f in result["findings"]], ["api.example.com"])
                self.assertFalse(result["capability_check_passes"])

    # Declaring the canary host clears only the capability finding, not the canary.
    def test_declared_canary_still_blocks(self):
        case = next(c for c in contacts.load_vectors()["cases"] if c["name"] == "canary-declared")
        self.assertEqual(contacts.evaluate(case), {
            "findings": [], "capability_check_passes": True, "static_canary_blocks": True,
        })


if __name__ == "__main__":
    unittest.main()
