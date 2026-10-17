"""Plant one narrowing mutant; the named vector test MUST exit nonzero."""

import argparse
import unittest
from unittest.mock import patch

import network_contacts as contacts
from test_network_contacts import NetworkContactTests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mutant", required=True, choices=("example-domain", "substring"))
    args = parser.parse_args()
    original = contacts.is_network_contact

    def mutant(host):
        normalized = contacts.normalize_host(host)
        if args.mutant == "example-domain" and normalized == "example.com":
            return False
        if args.mutant == "substring" and "test" in normalized:
            return False
        return original(host)

    suite = unittest.TestSuite([NetworkContactTests("test_network_contact_vectors")])
    with patch.object(contacts, "is_network_contact", side_effect=mutant):
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
