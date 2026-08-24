#!/usr/bin/env python3
"""Decide whether the pinned implementations actually consume this suite.

A pinned implementation job that exits 0 answers one question: did the pinned
build still pass? It never answered the question this repository cares about --
did the pinned build READ what this repository publishes? Schema 8 measured the
difference: both pinned managers exited 0 against a root carrying the whole
schema-8 surface while opening none of it.

`.github/ci/implementation-coverage.tsv` is this repository's own answer to the
second question, and this module enforces it in three parts:

    families  every artefact the ledger declares is still published by
              `conformance/v1/manifest.json`;
    go        every `go` row was observed PASSING in a real `go test -json`
              stream, with no skip of the case or any of its subtests;
    pytest    every `manager` row was observed PASSING in a real pytest
              `--junitxml` stream, covering every parameterization it produced.

Each part fails BY NAME. A renamed case, a deleted case, a package dropped from
the invocation, a selection matching nothing, a family removed from the suite
and a module-level skip are all loud rather than quiet, which is the property a
landing that advances implementation pins in the same commit as new normative
bytes depends on.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / ".github" / "ci" / "implementation-coverage.tsv"
DEFAULT_SUITE = ROOT / "conformance" / "v1"
IMPLEMENTATIONS = ("go", "manager")


class CoverageError(Exception):
    """One coverage claim this repository makes is not true of this run."""


@dataclass(frozen=True)
class Row:
    """One coverage claim: an implementation case and what it reads."""

    implementation: str
    identity: str
    artifacts: tuple[str, ...]
    behaviour: str

    @property
    def package(self) -> str:
        """The Go package of a `go` identity."""
        return self.identity.rsplit(".", 1)[0]

    @property
    def test(self) -> str:
        """The Go test name of a `go` identity."""
        return self.identity.rsplit(".", 1)[1]

    @property
    def module_path(self) -> str:
        """The dotted module a `manager` nodeid names, e.g. `tests.test_x`."""
        file_part = self.identity.split("::", 1)[0]
        return file_part[: -len(".py")].replace("/", ".")

    @property
    def function(self) -> str:
        """The test function a `manager` nodeid names."""
        return self.identity.split("::", 1)[1]


def load_ledger(path: Path = DEFAULT_LEDGER) -> tuple[Row, ...]:
    """Read the coverage ledger, rejecting a shape that cannot be enforced."""
    if not path.is_file():
        raise CoverageError(f"coverage ledger not found: {path}")
    rows: list[Row] = []
    seen: set[tuple[str, str]] = set()
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 4:
            raise CoverageError(
                f"{path}:{number}: expected 4 tab separated fields, got {len(fields)}"
            )
        implementation, identity, artifacts, behaviour = (f.strip() for f in fields)
        if implementation not in IMPLEMENTATIONS:
            raise CoverageError(
                f"{path}:{number}: unknown implementation {implementation!r}; "
                f"expected one of {', '.join(IMPLEMENTATIONS)}"
            )
        if not identity:
            raise CoverageError(f"{path}:{number}: row declares no identity")
        if implementation == "go" and "." not in identity:
            raise CoverageError(
                f"{path}:{number}: a go identity is `<package>.<TestName>`, got {identity!r}"
            )
        if implementation == "manager" and "::" not in identity:
            raise CoverageError(
                f"{path}:{number}: a manager identity is a pytest nodeid, got {identity!r}"
            )
        declared = tuple(part.strip() for part in artifacts.split(",") if part.strip())
        if not declared:
            raise CoverageError(f"{path}:{number}: {identity} declares no artefact")
        if not behaviour:
            raise CoverageError(f"{path}:{number}: {identity} declares no behaviour")
        key = (implementation, identity)
        if key in seen:
            raise CoverageError(f"{path}:{number}: {identity} is declared twice")
        seen.add(key)
        rows.append(Row(implementation, identity, declared, behaviour))
    if not rows:
        raise CoverageError(f"{path}: the coverage ledger declares no row")
    return tuple(rows)


def published_paths(suite: Path) -> frozenset[str]:
    """Read the published path set from the suite's own manifest."""
    manifest = suite / "manifest.json"
    if not manifest.is_file():
        raise CoverageError(f"conformance root has no manifest.json: {suite}")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CoverageError(f"conformance manifest is not valid JSON: {error}") from error
    entries = payload.get("files")
    if not isinstance(entries, list) or not entries:
        raise CoverageError("conformance manifest publishes no files")
    paths: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise CoverageError("conformance manifest entry publishes no path")
        paths.add(entry["path"])
    return frozenset(paths)


def missing_artifacts(
    declared: Iterable[str], paths: frozenset[str]
) -> tuple[str, ...]:
    """Name every declared artefact the suite does not publish.

    An artefact is either one published path or a family directory, which is
    published when the manifest publishes at least one file below it.
    """
    missing: list[str] = []
    for artifact in declared:
        prefix = artifact.rstrip("/") + "/"
        if artifact in paths:
            continue
        if any(path.startswith(prefix) for path in paths):
            continue
        missing.append(artifact)
    return tuple(missing)


def check_families(rows: Sequence[Row], suite: Path) -> list[str]:
    """Fail when this suite stopped publishing what the ledger claims is read."""
    paths = published_paths(suite)
    report: list[str] = []
    failures: list[str] = []
    for row in rows:
        missing = missing_artifacts(row.artifacts, paths)
        if missing:
            failures.append(
                f"{row.implementation}: {row.identity} reads "
                f"{', '.join(missing)}, which this suite does not publish"
            )
        else:
            report.append(f"served  {row.implementation}\t{row.identity}")
    if failures:
        raise CoverageError("\n".join(failures))
    return report


def go_observations(stream: Path) -> dict[tuple[str, str], set[str]]:
    """Collect every action `go test -json` reported for each named test.

    A subtest contributes its action to the parent it belongs to, so a skipped
    subtest of a required case is as fatal as skipping the case itself.
    """
    if not stream.is_file():
        raise CoverageError(f"no such go test stream: {stream}")
    observed: dict[tuple[str, str], set[str]] = {}
    for line in stream.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        action = event.get("Action")
        package = event.get("Package")
        test = event.get("Test")
        if action not in {"pass", "fail", "skip"} or not package or not test:
            continue
        observed.setdefault((package, test.split("/", 1)[0]), set()).add(action)
    return observed


def check_go(rows: Sequence[Row], stream: Path) -> list[str]:
    """Fail when a declared Go case was not observed passing in this run."""
    observed = go_observations(stream)
    report: list[str] = []
    failures: list[str] = []
    for row in (r for r in rows if r.implementation == "go"):
        suffix = "/" + row.package
        actions: set[str] = set()
        found = False
        for (package, test), seen in observed.items():
            if test != row.test:
                continue
            if package != row.package and not package.endswith(suffix):
                continue
            found = True
            actions |= seen
        if not found:
            failures.append(
                f"go: {row.identity} was not observed in this run -- "
                f"{row.behaviour}"
            )
            continue
        if "fail" in actions:
            failures.append(f"go: {row.identity} failed in this run")
            continue
        if "skip" in actions:
            failures.append(
                f"go: {row.identity} was skipped in this run; a declared "
                f"consumer may not skip against a serving root"
            )
            continue
        report.append(f"passed  go\t{row.identity}")
    if failures:
        raise CoverageError("\n".join(failures))
    return report


def pytest_observations(results: Path) -> list[tuple[str, str, str]]:
    """Collect `(classname, function, outcome)` from a pytest JUnit stream."""
    if not results.is_file():
        raise CoverageError(f"no such pytest result stream: {results}")
    try:
        tree = ElementTree.parse(results)
    except ElementTree.ParseError as error:
        raise CoverageError(f"pytest result stream is not valid XML: {error}") from error
    collected: list[tuple[str, str, str]] = []
    for case in tree.iter("testcase"):
        classname = case.get("classname") or ""
        name = (case.get("name") or "").split("[", 1)[0]
        outcome = "pass"
        for child in case:
            if child.tag == "skipped":
                outcome = "skip"
            elif child.tag in {"failure", "error"}:
                outcome = "fail"
                break
        collected.append((classname, name, outcome))
    return collected


def check_pytest(rows: Sequence[Row], results: Path) -> list[str]:
    """Fail when a declared manager case was not observed passing in this run."""
    collected = pytest_observations(results)
    report: list[str] = []
    failures: list[str] = []
    for row in (r for r in rows if r.implementation == "manager"):
        suffix = "." + row.module_path
        outcomes: list[str] = [
            outcome
            for classname, name, outcome in collected
            if name == row.function
            and (classname == row.module_path or classname.endswith(suffix))
        ]
        if not outcomes:
            failures.append(
                f"manager: {row.identity} was not observed in this run -- "
                f"{row.behaviour}"
            )
            continue
        if "fail" in outcomes:
            failures.append(f"manager: {row.identity} failed in this run")
            continue
        if "skip" in outcomes:
            failures.append(
                f"manager: {row.identity} was skipped in this run; a declared "
                f"consumer may not skip against a serving root"
            )
            continue
        report.append(f"passed  manager\t{row.identity}\t{len(outcomes)} case(s)")
    if failures:
        raise CoverageError("\n".join(failures))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_LEDGER,
        help="coverage ledger (default: .github/ci/implementation-coverage.tsv)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    families = subparsers.add_parser(
        "families", help="assert this suite still publishes every declared artefact"
    )
    families.add_argument("--root", type=Path, default=DEFAULT_SUITE)

    go = subparsers.add_parser(
        "go", help="assert every declared Go case was observed passing"
    )
    go.add_argument("--stream", type=Path, required=True)

    pytest_command = subparsers.add_parser(
        "pytest", help="assert every declared manager case was observed passing"
    )
    pytest_command.add_argument("--results", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        rows = load_ledger(args.ledger)
        if args.command == "families":
            report = check_families(rows, args.root)
        elif args.command == "go":
            report = check_go(rows, args.stream)
        else:
            report = check_pytest(rows, args.results)
    except CoverageError as error:
        print("implementation-coverage: FAILED", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1
    for line in report:
        print(f"implementation-coverage: {line}")
    print(f"implementation-coverage: {len(report)} declared claim(s) upheld")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
