from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import implementation_coverage as coverage


SOURCE_ROOT = Path(__file__).resolve().parents[1]

GO_ROW = (
    "go\tinternal/scriptpolicy.TestScriptExecutionOptInCases\t"
    "vectors/script-host-execution-policy.json\tevery published opt-in case decides acceptance"
)
MANAGER_ROW = (
    "manager\ttests/test_schema8_candidate_conformance.py::test_module_root_case\t"
    "vectors/module-roots.json\tevery published module-roots case reaches its failure boundary"
)
LEDGER = f"# implementation\tidentity\tartefacts\tbehaviour\n{GO_ROW}\n{MANAGER_ROW}\n"


def go_event(action: str, test: str, package: str = "example.com/m/internal/scriptpolicy") -> str:
    return json.dumps({"Action": action, "Package": package, "Test": test})


def junit(cases: list[tuple[str, str, str | None]]) -> str:
    body = []
    for classname, name, outcome in cases:
        if outcome is None:
            body.append(f'<testcase classname="{classname}" name="{name}"/>')
        else:
            body.append(
                f'<testcase classname="{classname}" name="{name}">'
                f'<{outcome} message="x"/></testcase>'
            )
    return f'<?xml version="1.0"?><testsuites><testsuite>{"".join(body)}</testsuite></testsuites>'


class LedgerShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def write(self, text: str) -> Path:
        path = self.root / "ledger.tsv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_the_shipped_ledger_loads(self) -> None:
        rows = coverage.load_ledger()
        self.assertTrue(rows)
        self.assertEqual({row.implementation for row in rows}, {"go", "manager"})

    def test_comments_and_blank_lines_are_not_rows(self) -> None:
        rows = coverage.load_ledger(self.write(LEDGER + "\n#  trailing note\n"))
        self.assertEqual(len(rows), 2)

    def test_a_row_with_the_wrong_field_count_is_rejected(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.load_ledger(self.write("go\tinternal/x.TestY\tvectors/a.json\n"))

    def test_an_unknown_implementation_is_rejected(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.load_ledger(self.write("rust\tinternal/x.TestY\tv/a.json\twhy\n"))

    def test_a_go_identity_without_a_package_is_rejected(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.load_ledger(self.write("go\tTestY\tv/a.json\twhy\n"))

    def test_a_manager_identity_without_a_nodeid_is_rejected(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.load_ledger(self.write("manager\ttests/x.py\tv/a.json\twhy\n"))

    def test_a_row_declaring_no_artefact_is_rejected(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.load_ledger(self.write("go\tinternal/x.TestY\t\twhy\n"))

    def test_a_duplicate_identity_is_rejected(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.load_ledger(self.write(f"{GO_ROW}\n{GO_ROW}\n"))

    def test_an_empty_ledger_is_rejected(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.load_ledger(self.write("# only a comment\n"))


class FamilyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.ledger = self.root / "ledger.tsv"
        self.ledger.write_text(LEDGER, encoding="utf-8")
        self.suite = self.root / "conformance" / "v1"
        self.suite.mkdir(parents=True)

    def publish(self, *paths: str) -> None:
        (self.suite / "manifest.json").write_text(
            json.dumps({"files": [{"path": path} for path in paths]}),
            encoding="utf-8",
        )

    def test_a_published_file_and_a_published_family_are_both_served(self) -> None:
        self.publish(
            "vectors/script-host-execution-policy.json",
            "vectors/module-roots.json",
        )
        report = coverage.check_families(coverage.load_ledger(self.ledger), self.suite)
        self.assertEqual(len(report), 2)

    def test_a_family_directory_counts_as_published_by_one_member(self) -> None:
        ledger = self.root / "family.tsv"
        ledger.write_text(
            "go\tinternal/skillspec.TestReleasedSchemaCases\t"
            "schema-cases/agent-skill-v8\tboth halves are loaded\n",
            encoding="utf-8",
        )
        self.publish("schema-cases/agent-skill-v8/valid.json")
        self.assertEqual(len(coverage.check_families(coverage.load_ledger(ledger), self.suite)), 1)

    def test_removing_a_declared_family_from_the_suite_fails_by_name(self) -> None:
        self.publish("vectors/script-host-execution-policy.json")
        with self.assertRaises(coverage.CoverageError) as caught:
            coverage.check_families(coverage.load_ledger(self.ledger), self.suite)
        self.assertIn("vectors/module-roots.json", str(caught.exception))

    def test_a_root_without_a_manifest_fails(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.check_families(coverage.load_ledger(self.ledger), self.suite)

    def test_a_manifest_publishing_no_file_fails(self) -> None:
        (self.suite / "manifest.json").write_text('{"files": []}', encoding="utf-8")
        with self.assertRaises(coverage.CoverageError):
            coverage.check_families(coverage.load_ledger(self.ledger), self.suite)

    def test_the_shipped_ledger_is_served_by_the_shipped_suite(self) -> None:
        report = coverage.check_families(
            coverage.load_ledger(), SOURCE_ROOT / "conformance" / "v1"
        )
        self.assertEqual(len(report), len(coverage.load_ledger()))


class GoStreamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.ledger = self.root / "ledger.tsv"
        self.ledger.write_text(GO_ROW + "\n", encoding="utf-8")

    def stream(self, *lines: str) -> Path:
        path = self.root / "go-test.json"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def rows(self) -> tuple[coverage.Row, ...]:
        return coverage.load_ledger(self.ledger)

    def test_a_passing_case_is_upheld(self) -> None:
        stream = self.stream(go_event("pass", "TestScriptExecutionOptInCases"))
        self.assertEqual(len(coverage.check_go(self.rows(), stream)), 1)

    def test_non_json_build_output_is_ignored(self) -> None:
        stream = self.stream(
            "# example.com/m/internal/scriptpolicy",
            go_event("pass", "TestScriptExecutionOptInCases"),
        )
        self.assertEqual(len(coverage.check_go(self.rows(), stream)), 1)

    def test_a_renamed_case_fails_by_name(self) -> None:
        stream = self.stream(go_event("pass", "TestScriptExecutionOptInCasesRenamed"))
        with self.assertRaises(coverage.CoverageError) as caught:
            coverage.check_go(self.rows(), stream)
        self.assertIn("was not observed", str(caught.exception))

    def test_a_case_in_another_package_does_not_satisfy_the_row(self) -> None:
        stream = self.stream(
            go_event(
                "pass",
                "TestScriptExecutionOptInCases",
                package="example.com/m/internal/other",
            )
        )
        with self.assertRaises(coverage.CoverageError):
            coverage.check_go(self.rows(), stream)

    def test_a_failed_case_fails(self) -> None:
        stream = self.stream(go_event("fail", "TestScriptExecutionOptInCases"))
        with self.assertRaises(coverage.CoverageError) as caught:
            coverage.check_go(self.rows(), stream)
        self.assertIn("failed", str(caught.exception))

    def test_a_skipped_case_fails(self) -> None:
        stream = self.stream(go_event("skip", "TestScriptExecutionOptInCases"))
        with self.assertRaises(coverage.CoverageError) as caught:
            coverage.check_go(self.rows(), stream)
        self.assertIn("skipped", str(caught.exception))

    def test_a_skipped_subtest_fails_its_parent(self) -> None:
        stream = self.stream(
            go_event("pass", "TestScriptExecutionOptInCases"),
            go_event("skip", "TestScriptExecutionOptInCases/declared-only"),
        )
        with self.assertRaises(coverage.CoverageError) as caught:
            coverage.check_go(self.rows(), stream)
        self.assertIn("skipped", str(caught.exception))

    def test_an_empty_run_fails(self) -> None:
        stream = self.stream("")
        with self.assertRaises(coverage.CoverageError):
            coverage.check_go(self.rows(), stream)

    def test_a_missing_stream_fails(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.check_go(self.rows(), self.root / "absent.json")


class PytestStreamTests(unittest.TestCase):
    MODULE = "tests.test_schema8_candidate_conformance"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.ledger = self.root / "ledger.tsv"
        self.ledger.write_text(MANAGER_ROW + "\n", encoding="utf-8")

    def results(self, cases: list[tuple[str, str, str | None]]) -> Path:
        path = self.root / "results.xml"
        path.write_text(junit(cases), encoding="utf-8")
        return path

    def rows(self) -> tuple[coverage.Row, ...]:
        return coverage.load_ledger(self.ledger)

    def test_every_parameterization_is_covered_by_one_row(self) -> None:
        results = self.results(
            [(self.MODULE, f"test_module_root_case[case-{index}]", None) for index in range(10)]
        )
        report = coverage.check_pytest(self.rows(), results)
        self.assertEqual(len(report), 1)
        self.assertIn("10 case(s)", report[0])

    def test_a_nested_classname_prefix_still_matches(self) -> None:
        results = self.results(
            [(f"implementations.manager.{self.MODULE}", "test_module_root_case[a]", None)]
        )
        self.assertEqual(len(coverage.check_pytest(self.rows(), results)), 1)

    def test_a_renamed_case_fails_by_name(self) -> None:
        results = self.results([(self.MODULE, "test_module_root_case_renamed[a]", None)])
        with self.assertRaises(coverage.CoverageError) as caught:
            coverage.check_pytest(self.rows(), results)
        self.assertIn("was not observed", str(caught.exception))

    def test_a_case_from_another_module_does_not_satisfy_the_row(self) -> None:
        results = self.results([("tests.test_other", "test_module_root_case[a]", None)])
        with self.assertRaises(coverage.CoverageError):
            coverage.check_pytest(self.rows(), results)

    def test_a_failed_parameterization_fails_the_row(self) -> None:
        results = self.results(
            [
                (self.MODULE, "test_module_root_case[a]", None),
                (self.MODULE, "test_module_root_case[b]", "failure"),
            ]
        )
        with self.assertRaises(coverage.CoverageError) as caught:
            coverage.check_pytest(self.rows(), results)
        self.assertIn("failed", str(caught.exception))

    def test_an_errored_parameterization_fails_the_row(self) -> None:
        results = self.results([(self.MODULE, "test_module_root_case[a]", "error")])
        with self.assertRaises(coverage.CoverageError):
            coverage.check_pytest(self.rows(), results)

    def test_a_module_level_skip_fails_the_row(self) -> None:
        results = self.results([(self.MODULE, "test_module_root_case[a]", "skipped")])
        with self.assertRaises(coverage.CoverageError) as caught:
            coverage.check_pytest(self.rows(), results)
        self.assertIn("skipped", str(caught.exception))

    def test_an_empty_run_fails(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.check_pytest(self.rows(), self.results([]))

    def test_a_missing_stream_fails(self) -> None:
        with self.assertRaises(coverage.CoverageError):
            coverage.check_pytest(self.rows(), self.root / "absent.xml")


class CommandLineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def run_quietly(self, argv: list[str]) -> int:
        """Run the command line without its report reaching this test's output."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            return coverage.main(argv)

    def test_families_returns_zero_for_the_shipped_suite(self) -> None:
        self.assertEqual(
            self.run_quietly(
                ["families", "--root", str(SOURCE_ROOT / "conformance" / "v1")]
            ),
            0,
        )

    def test_go_returns_one_when_a_declared_case_is_absent(self) -> None:
        stream = self.root / "go-test.json"
        stream.write_text(go_event("pass", "TestSomethingElse") + "\n", encoding="utf-8")
        self.assertEqual(self.run_quietly(["go", "--stream", str(stream)]), 1)

    def test_pytest_returns_one_when_a_declared_case_is_absent(self) -> None:
        results = self.root / "results.xml"
        results.write_text(junit([("tests.test_other", "test_other", None)]), encoding="utf-8")
        self.assertEqual(self.run_quietly(["pytest", "--results", str(results)]), 1)


if __name__ == "__main__":
    unittest.main()
