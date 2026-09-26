from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SIGNERS = ROOT / "maintainers.allowed_signers"

MAINTAINER_LINE = (
    "oparin@me.com ecdsa-sha2-nistp256 "
    "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBCUyTf/+Zsam+4ftpv2aNxP86CmTlsfxXxo6XySRIKx2LN+UDVM6ftmPQHBJuedkg4KSIcu9H107FRkUMqjOnso="
)
BOT_LINE = (
    "bot@relux.works ssh-ed25519 "
    "AAAAC3NzaC1lZDI1NTE5AAAAIPG7xTX05HL1XaD4XLUk0/TTeqRNHbMj5HdnqNQdDTID"
)

KNOWN_KEY_TYPES = {"ecdsa-sha2-nistp256", "ssh-ed25519"}


class SignerLineError(ValueError):
    pass


def parse_allowed_signers_line(line: str) -> tuple[str, str, str]:
    parts = line.split(" ")
    if len(parts) != 3 or not all(parts):
        raise SignerLineError(f"malformed allowed_signers line: {line!r}")
    principal, key_type, key = parts
    if "@" not in principal:
        raise SignerLineError(f"principal is not an email: {principal!r}")
    if key_type not in KNOWN_KEY_TYPES:
        raise SignerLineError(f"unknown key type: {key_type!r}")
    return principal, key_type, key


class AllowedSignersFileTests(unittest.TestCase):
    def test_file_is_expected_two_lines(self) -> None:
        raw = ALLOWED_SIGNERS.read_bytes()
        self.assertTrue(raw.endswith(b"\n"), "file must end with a trailing newline")
        lines = raw.decode("utf-8").splitlines()
        self.assertEqual(lines, [MAINTAINER_LINE, BOT_LINE])

    def test_maintainer_line_byte_identical(self) -> None:
        lines = ALLOWED_SIGNERS.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], MAINTAINER_LINE)

    def test_bot_line_exact(self) -> None:
        lines = ALLOWED_SIGNERS.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[1], BOT_LINE)

    def test_principals_are_unique_and_known(self) -> None:
        principals = [parse_allowed_signers_line(line)[0] for line in ALLOWED_SIGNERS.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sorted(principals), ["bot@relux.works", "oparin@me.com"])

    def test_rejects_malformed_line(self) -> None:
        with self.assertRaises(SignerLineError):
            parse_allowed_signers_line("bot@relux.works ssh-ed25519")

    def test_rejects_unknown_key_type(self) -> None:
        with self.assertRaises(SignerLineError):
            parse_allowed_signers_line("bot@relux.works ssh-rsa AAAA")

    def test_rejects_non_email_principal(self) -> None:
        with self.assertRaises(SignerLineError):
            parse_allowed_signers_line("bot ssh-ed25519 AAAA")


if __name__ == "__main__":
    unittest.main()
