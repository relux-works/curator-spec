"""Controls for draft schemas and checker; no production or runtime evidence."""
import copy
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import claude_env_carriers as carriers


class CarrierTests(unittest.TestCase):
    # Published positive/negative controls exercise actual schema references;
    # passing them does not prove exhaustive final #216 compatibility.
    def test_published_corpus(self):
        output = io.StringIO()
        self.assertEqual(carriers.run(carriers.ROOT, output), 0, output.getvalue())
        self.assertIn("failures=0 final-predecessor-parity=unverified runtime-cases=0", output.getvalue())

    # An unrelated broken carrier with a valid member is setup failure, never
    # detection of a member defect; the otherwise identical valid carrier passes.
    def test_carrier_setup_control(self):
        validator = carriers.validators(carriers.ROOT)["configuration"]
        self.assertGreater(carriers.declaration_controls(carriers.ROOT, validator), 0)
        prefix = '{"schema_version":9,"skills_root":"/example/skills","projects":{},"extra":true,"extensions":{"claude_env":'
        with self.assertRaisesRegex(carriers.SetupError, "^carrier-setup$"):
            carriers.declaration_controls(carriers.ROOT, validator, prefix)

    # A published complete schema-5 control remains valid after explicit version
    # migration and addition of the Claude member. An unknown sibling still
    # rejects; this one witness is not exhaustive final schema-8 preservation.
    def test_published_predecessor_control(self):
        path = carriers.ROOT / "conformance/rc7-carriers-v1/cases/config-valid.json"
        original = carriers.strict(path.read_bytes())
        candidate = copy.deepcopy(original)
        candidate["schema_version"] = 9
        candidate["extensions"] = {"claude_env": {"BASH_MAX_OUTPUT_LENGTH": "8000"}}
        validator = carriers.validators(carriers.ROOT)["configuration"]
        self.assertTrue(validator.is_valid(candidate))
        candidate["extensions"]["unknown"] = {}
        self.assertFalse(validator.is_valid(candidate))
        self.assertEqual(carriers.strict(path.read_bytes()), original)

    # Every admitted configuration fixture in the schema-8 corpus retains its
    # structural verdict in 9, both without and with the new Claude leaf. This
    # is bounded corpus preservation, not exhaustive native-reader equivalence.
    def test_stacked_notification_predecessor_controls(self):
        validator = carriers.validators(carriers.ROOT)["configuration"]
        path = carriers.ROOT / "conformance/host-notification-v1/cases.json"
        count = 0
        for case in carriers.strict(path.read_bytes()):
            if case["entry"] != "configuration" or case["expected"][0] != "ok":
                continue
            candidate = carriers.strict(case["input_json"])
            candidate["schema_version"] = 9
            self.assertTrue(validator.is_valid(candidate), case["id"])
            candidate.setdefault("extensions", {})["claude_env"] = {"BASH_MAX_OUTPUT_LENGTH": "8000"}
            self.assertTrue(validator.is_valid(candidate), case["id"])
            count += 1
        self.assertGreater(count, 0)

    # Reviewer P1 must admit both forbidden predecessor members under mutation,
    # while each same-carrier positive control still passes. P2-P4 independently
    # detect wrong envelope pairing and loss of predecessor members. No runtime.
    def test_reviewer_schema_plants(self):
        plants = (
            ('predecessor', 'host-notification-v1/extensions.schema.json',
             ('schema8-claude-env-refused', 'launcher2-claude-env-refused'), True),
            ('pair', 'machine-claude-env-v1/launcher-config-v3.schema.json',
             ('launcher-old-config',), True),
            ('notification', 'machine-claude-env-v1/extensions.schema.json',
             ('configuration-notification-host',), False),
            ('build', 'machine-claude-env-v1/manager-config-v9.schema.json',
             ('configuration-unrelated-fields',), False),
        )
        original_cases = carriers.load_cases(carriers.ROOT)
        for kind, filename, witnesses, planted_valid in plants:
            with self.subTest(plant=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                shutil.copytree(carriers.ROOT / 'schemas', root / 'schemas')
                shutil.copytree(carriers.ROOT / 'conformance' / carriers.NAMESPACE,
                                root / 'conformance' / carriers.NAMESPACE)
                path = root / 'schemas' / filename
                schema = json.loads(path.read_text())
                if kind == 'predecessor':
                    schema['properties']['claude_env'] = {
                        '$ref': '../machine-claude-env-v1/claude-env.schema.json'}
                elif kind == 'pair':
                    schema['properties']['config_schema'] = {'enum': [8, 9]}
                elif kind == 'notification':
                    del schema['properties']['notification']
                else:
                    del schema['properties']['build_ssh']
                path.write_text(json.dumps(schema))
                compiled = carriers.validators(root)
                for witness in witnesses:
                    case = next(c for c in original_cases if c['id'] == witness)
                    self.assertEqual(compiled[case['entry']].is_valid(carriers.strict(case['input_json'])), planted_valid)
                if kind == 'predecessor':
                    for name in ('schema8-control', 'launcher2-control'):
                        case = next(c for c in original_cases if c['id'] == name)
                        self.assertTrue(compiled[case['entry']].is_valid(carriers.strict(case['input_json'])))
                output = io.StringIO()
                self.assertEqual(carriers.run(root, output), 1, output.getvalue())
                for witness in witnesses:
                    self.assertIn('FAIL ' + witness + ' ', output.getvalue())
        self.assertEqual(carriers.run(carriers.ROOT, io.StringIO()), 0)

    # Wrong expected acceptance and rejection each fail the command aggregate
    # with exit 1; later cases run and no input/schema details are reflected.
    def test_checker_violation_controls(self):
        original = carriers.load_cases(carriers.ROOT)
        for verdict in (True, False):
            changed = copy.deepcopy(original)
            index = next(i for i, case in enumerate(changed) if case["schema_valid"] == verdict)
            changed[index]["schema_valid"] = not verdict
            output = io.StringIO()
            with patch.object(carriers, "load_cases", return_value=changed):
                self.assertEqual(carriers.run(carriers.ROOT, output), 1)
            self.assertIn("FAIL " + changed[index]["id"], output.getvalue())
            self.assertIn("PASS " + changed[-1]["id"], output.getvalue())
            self.assertIn("failures=1", output.getvalue())
            self.assertNotIn("8000", output.getvalue())

    # Corpus metadata refuses ambiguity, unknown/missing/wrongly typed fields
    # and malformed bytes; restored input passes in the same isolated fixture.
    def test_strict_corpus_controls(self):
        original = (carriers.ROOT / "conformance" / carriers.NAMESPACE / "containing-cases.json").read_bytes()
        for fault in ("duplicate", "escaped-duplicate", "unknown", "missing", "wrong-type", "invalid-utf8", "trailing", "case-variant"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name in carriers.RESOURCES:
                    destination = root / "schemas" / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(carriers.ROOT / "schemas" / name, destination)
                corpus = root / "conformance" / carriers.NAMESPACE
                corpus.mkdir(parents=True)
                shutil.copyfile(carriers.ROOT / "conformance" / carriers.NAMESPACE / "cases.json", corpus / "cases.json")
                path = corpus / "containing-cases.json"
                path.write_bytes(original)
                self.assertEqual(carriers.run(root, io.StringIO()), 0)
                rows = json.loads(original)
                if fault == "unknown": rows[0]["unexpected"] = "MUST_NOT_APPEAR"
                if fault == "missing": del rows[0]["claim"]
                if fault == "wrong-type": rows[0]["schema_valid"] = "true"
                if fault == "case-variant": rows[0]["ID"] = rows[0].pop("id")
                raw = json.dumps(rows).encode()
                if fault == "duplicate": raw = raw.replace(b'"id":', b'"id":"MUST_NOT_APPEAR","id":', 1)
                if fault == "escaped-duplicate": raw = raw.replace(b'"id":', b'"\\u0069d":"MUST_NOT_APPEAR","id":', 1)
                if fault == "invalid-utf8": raw = b'\xff' + raw
                if fault == "trailing": raw += b' []'
                path.write_bytes(raw)
                output = io.StringIO()
                self.assertEqual(carriers.run(root, output), 2)
                self.assertEqual(output.getvalue(), "FAIL containing-setup\n")
                path.write_bytes(original)
                self.assertEqual(carriers.run(root, io.StringIO()), 0)

    # Strict input rejects duplicate decoded keys, non-JSON constants and trailing
    # input; a nearby valid file remains readable without last-wins behavior.
    def test_strict_file_pairs(self):
        self.assertEqual(carriers.strict(b'{"x":1}'), {"x": 1})
        for raw in (b'{"x":1,"\\u0078":2}', b'{} {}', b'{"x":NaN}', b'{"x":1,}', b'\xff', b'\xef\xbb\xbf{}'):
            with self.assertRaises(carriers.SetupError):
                carriers.strict(raw)


if __name__ == "__main__":
    unittest.main()
