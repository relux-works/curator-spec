#!/usr/bin/env python3
"""Run a pytest suite and turn every skipped test into a gate failure."""

from __future__ import annotations

import sys

import pytest


class NoSkips:
    def __init__(self) -> None:
        self.nodeids: set[str] = set()

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.skipped:
            self.nodeids.add(report.nodeid)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.skipped:
            self.nodeids.add(report.nodeid)


def main() -> int:
    gate = NoSkips()
    result = pytest.main(sys.argv[1:], plugins=[gate])
    if gate.nodeids:
        print("conformance gate: skipped tests are forbidden", file=sys.stderr)
        for nodeid in sorted(gate.nodeids):
            print(f"- {nodeid}", file=sys.stderr)
        return 1
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
