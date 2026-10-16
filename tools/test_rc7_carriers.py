"""Publication tests; no runtime readiness, transaction or delivery qualification."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rc7_carriers as carriers
from test_validate import validate


ROOT = validate.ROOT
CORPUS = ROOT / "conformance/rc7-carriers-v1"
KEY = "cli_auth_credentials_store"


class CarrierTests(unittest.TestCase):
    def setUp(self):
        self.resources, self.schemas = carriers.registry(ROOT, validate.load_json)

    def case(self, name):
        return validate.load_json(CORPUS / "cases" / (name + ".json"))

    def error(self, schema, instance):
        before = copy.deepcopy(instance)
        actual = carriers.carrier_error(schema, instance, self.schemas, self.resources,
                                        validate.validate_wire_semantics)
        self.assertEqual(instance, before, "spec validation must not mutate its input")
        return actual

    def old_validator(self, name):
        return validate.Draft202012Validator(
            validate.load_json(ROOT / "schemas/v1" / (name + ".schema.json")),
            registry=self.resources)

    # Complete old and new controls validate only under their own wire readers;
    # unknown additions/tokens cannot turn old envelopes into new ones.
    def test_compatibility_dispatch_and_v4_ownership(self):
        for case in validate.load_json(CORPUS / "compatibility.json"):
            with self.subTest(carrier=case["new_schema"]):
                old = validate.load_json(ROOT / case["old_control"])
                new = validate.load_json(CORPUS / case["new_control"])
                reader = self.old_validator(case["old_schema"])
                self.assertTrue(reader.is_valid(old))
                self.assertIsNone(self.error(case["new_schema"], new))
                self.assertFalse(reader.is_valid(new))
                self.assertEqual(self.error(case["new_schema"], old), "carrier_schema_invalid")
                injected = copy.deepcopy(old)
                injected["codex_settings"] = {}
                self.assertFalse(reader.is_valid(injected))
                invented = copy.deepcopy(new)
                invented[case["discriminator"]] = 999
                self.assertEqual(self.error(case["new_schema"], invented), "carrier_schema_invalid")

    # Config 1–3 controls retain meaning and reject the new selector. Config 5
    # validates the entire document, including fields outside the frozen subtree.
    def test_config_enclosing_fields_and_old_readers(self):
        valid = self.case("config-valid")
        self.assertIsNone(self.error("manager-config-v5", valid))
        for version in (1, 2, 3):
            old = {"schema_version": version, "skills_root": "/manager/skills", "projects": {}}
            reader = self.old_validator(f"manager-config-v{version}")
            self.assertTrue(reader.is_valid(old))
            old["environments"] = {"credential_store": valid["environments"]["credential_store"]}
            self.assertFalse(reader.is_valid(old))
        for name in ("config-missing-enclosing-field", "config-unknown-store", "config-unknown-environment"):
            self.assertEqual(self.error("manager-config-v5", self.case(name)), "carrier_schema_invalid")

    # The independent allocation does not repurpose CIP-0013's proposed wire
    # numbers. No base-context adoption is implied by these new schemas.
    def test_draft_reserved_versions_are_not_repurposed(self):
        for schema, control, key, reserved in (
            ("manager-config-v5", "config-valid", "schema_version", 4),
            ("context-lock-v4", "lock-empty", "schema_version", 3),
            ("agent-environment-marker-v5", "marker-empty", "version", 4),
        ):
            valid = self.case(control)
            self.assertIsNone(self.error(schema, valid))
            valid[key] = reserved
            self.assertEqual(self.error(schema, valid), "carrier_schema_invalid")

    # A valid standalone row cannot attest a malformed status wrapper; both
    # wrapper fields and the imported closed row are enforced without input writes.
    def test_status_enclosing_fields_and_secret_closure(self):
        valid = self.case("status-present")
        self.assertIsNone(self.error("env-status-v1", valid))
        row_schema = validate.load_json(ROOT / "schemas/login-readiness-v1/login-row-v1.schema.json")
        broken = self.case("status-missing-enclosing-field")
        self.assertTrue(validate.Draft202012Validator(row_schema, registry=self.resources).is_valid(
            broken["rows"][0]["readiness"]))
        for name in ("status-missing-enclosing-field", "status-invalid-imported-row",
                     "status-secret-field", "status-account-field"):
            self.assertEqual(self.error("env-status-v1", self.case(name)), "carrier_schema_invalid")

    # Every required successor enclosing field remains required, independently
    # of its imported projection. A complete carrier is the positive control.
    def test_full_carrier_required_members(self):
        for schema in sorted(self.schemas):
            path = next(c["instance"] for c in validate.load_json(CORPUS / "index.json")
                        if c["schema"] == schema and c["error"] is None)
            valid = validate.load_json(CORPUS / path)
            self.assertIsNone(self.error(schema, valid))
            for member in self.schemas[schema]["required"]:
                with self.subTest(schema=schema, member=member):
                    broken = copy.deepcopy(valid)
                    broken.pop(member)
                    self.assertEqual(self.error(schema, broken), "carrier_schema_invalid")

    # Empty/absent package settings are valid; store/account policy in any
    # package-derived carrier (even a losing contribution) cannot be admitted.
    def test_package_authority_and_empty_provenance(self):
        for name in ("manifest-absent", "manifest-empty"):
            self.assertIsNone(self.error("agent-context-v2", self.case(name)))
        for schema, control, key in (("agent-context-v2", "manifest-empty", "codex_settings"),
                                     ("context-lock-v4", "lock-empty", "codex_settings"),
                                     ("agent-environment-marker-v5", "marker-empty", "codex_settings")):
            self.assertIsNone(self.error(schema, self.case(control)))
            for payload in ({KEY: "file"}, {"account": "forbidden"}, {"credential_store": "file"}):
                broken = self.case(control)
                broken[key] = payload
                self.assertEqual(self.error(schema, broken), "carrier_schema_invalid")
        for name in ("lock-losing-package-store", "lock-empty-contribution-entry", "lock-machine-store"):
            self.assertEqual(self.error("context-lock-v4", self.case(name)), "carrier_schema_invalid")
        reader = self.old_validator("system-config-v2")
        valid = {"schema_version": 2, "environments": {"isolation": {"example": {"muse": "isolated"}}}}
        self.assertTrue(reader.is_valid(valid))
        for key in ("credential_store", "credential_source", "account", "codex_settings"):
            broken = copy.deepcopy(valid)
            broken["environments"][key] = {}
            self.assertFalse(reader.is_valid(broken))
            self.assertFalse(reader.is_valid({"schema_version": 2, "locked": ["environments." + key]}))

    # Native omits typed settings; explicit file/keyring grammar requires exactly
    # one matching payload. These cases do not qualify a store or its custody.
    def test_single_typed_payload_required_and_agrees(self):
        for name in ("fragment-native", "fragment-native-absent", "fragment-file", "fragment-keyring-grammar-only"):
            self.assertIsNone(self.error("launch-env-fragment-v5", self.case(name)))
        for name in ("fragment-dropped-transport", "fragment-selection-mismatch", "fragment-competing-owner",
                     "fragment-unbound-payload", "fragment-empty-payload"):
            self.assertEqual(self.error("launch-env-fragment-v5", self.case(name)), "carrier_schema_invalid")
        native = self.case("fragment-native")
        native["codex_settings"] = {KEY: "file"}
        self.assertEqual(self.error("launch-env-fragment-v5", native), "carrier_schema_invalid")

    # V5 retains v4 Muse one-parent/five-value and non-Codex payload boundaries.
    def test_muse_and_other_adapter_boundaries(self):
        self.assertIsNone(self.error("launch-env-fragment-v5", self.case("fragment-muse-five-values")))
        self.assertEqual(self.error("launch-env-fragment-v5", self.case("fragment-muse-foreign-parent")),
                         "carrier_semantics_invalid")
        for env in ("muse", "claude_code", "pi", "opencode"):
            self.assertEqual(self.error("launch-env-fragment-v5", self.case("fragment-" + env + "-codex-payload")),
                             "carrier_schema_invalid")

    # The published matrix keeps configured/native/effective storage distinct;
    # OpenCode unknown is not present. Aggregate runtime execution remains unrun.
    def test_status_store_and_ambient_invariants(self):
        for name in ("status-muse-native", "status-muse-file", "status-opencode-unknown"):
            self.assertIsNone(self.error("env-status-v1", self.case(name)))
        for name in ("status-mismatch-effective", "status-duplicate-row",
                     "status-missing-settings-provenance", "status-opencode-invented-present"):
            self.assertEqual(self.error("env-status-v1", self.case(name)), "carrier_semantics_invalid")

    # Regression: a known Muse home/shared candidate requires file metadata;
    # external sources and unknown/source-conflict rows are separate contracts.
    def test_muse_status_source_backend_regression(self):
        for configured in ("native", "file"):
            for source in ("per-home", "native"):
                for login, reason in (("present", "candidate-present"), ("absent", "candidate-absent")):
                    with self.subTest(configured=configured, source=source, login=login):
                        valid = self.case("status-muse-native")
                        valid["rows"][0]["configured_store"] = configured
                        readiness = valid["rows"][0]["readiness"]
                        readiness["login"] = login
                        readiness["login_detail"].update(source=source, reason=reason)
                        self.assertIsNone(self.error("env-status-v1", valid))
                        for backend in ("keychain", "environment", "external"):
                            broken = copy.deepcopy(valid)
                            broken["rows"][0]["readiness"]["login_detail"]["backend"] = backend
                            self.assertEqual(self.error("env-status-v1", broken), "carrier_semantics_invalid")

        for source, backend in (("environment", "environment"), ("node", "external"),
                                ("helper", "external"), ("broker", "external")):
            valid = self.case("status-muse-native")
            valid["rows"][0]["readiness"]["login_detail"].update(source=source, backend=backend)
            self.assertIsNone(self.error("env-status-v1", valid))
        for reason in ("metadata-unavailable", "source-conflict", "unqualified-backend"):
            for backend in ("unknown", "file", "keychain"):
                valid = self.case("status-muse-native")
                valid["rows"][0]["readiness"]["login"] = "unknown"
                valid["rows"][0]["readiness"]["login_detail"].update(backend=backend, reason=reason)
                self.assertIsNone(self.error("env-status-v1", valid))

    # Duplicates and bad encoding fail before decoding/schema admission. No
    # claim about a vendor parser or a remote receiver is made.
    def test_duplicate_keys_and_invalid_utf8(self):
        valid = self.case("fragment-file")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "carrier.json"
            path.write_text(json.dumps(valid))
            self.assertEqual(validate.load_json(path), valid)
            path.write_text(json.dumps(valid)[:-1] + ',"fragment":"launch-env-fragment-v5"}')
            with self.assertRaisesRegex(validate.ValidationFailure, "duplicate JSON key 'fragment'"):
                validate.load_json(path)
            path.write_bytes(b'{"fragment":"\xff"}')
            with self.assertRaisesRegex(validate.ValidationFailure, "invalid JSON: 'utf-8' codec"):
                validate.load_json(path)

    # Exact canonical bytes, full carrier verdicts and production dispatch agree.
    def test_production_corpus_and_canonical_bytes(self):
        total, negatives = carriers.check_corpus(ROOT, validate.load_json, validate.ccj1_bytes,
                                                 validate.validate_wire_semantics)
        self.assertGreater(total, negatives)
        self.assertGreater(negatives, 0)
        validate.validate_rc7_carriers()

    # Plant one wrong enclosing discriminator beside its valid control; the
    # actual production gate must reject that named case, not fail setup.
    def test_bounded_invalid_containing_carrier_plant(self):
        validate.validate_rc7_carriers()
        original = validate.load_json

        def planted(path):
            value = original(path)
            if path == CORPUS / "cases/config-valid.json":
                value["schema_version"] = 3
            return value

        with patch.object(validate, "load_json", side_effect=planted):
            with self.assertRaisesRegex(validate.ValidationFailure,
                                        "config-valid: expected None, got carrier_schema_invalid"):
                validate.validate_rc7_carriers()

    # These pin the published seam decisions and CLI text only: no fake runtime
    # adapter or projection checker is substituted for consumer qualification.
    def test_published_muse_decision_table(self):
        try:
            carriers.check_decisions(ROOT, validate.load_json)
        except carriers.ContractError as exc:
            self.fail(str(exc))
        publication = (ROOT / "protocol/rc7-carriers.md").read_text()
        self.assertIn("Muse explicit keychain | `environment_credential_store_unsupported`", publication)
        self.assertIn("Ambient backend is not an explicit operator override", publication)
        self.assertIn("Credential-source\nconflicts are separate", publication)
        self.assertIn("effective file, selector unchanged", publication)

    # The status exception cannot silently widen to version/auth probes; these
    # are specification assertions, not evidence of zero runtime effects.
    def test_status_no_agent_execution_published(self):
        publication = (ROOT / "protocol/rc7-carriers.md").read_text()
        self.assertIn("Adopting readiness status executes no agent binary, including --version or auth status.", publication)
        env = (ROOT / "protocol/environments.md").read_text()
        self.assertNotIn("(`<tool> --version`", env)
        self.assertIn("no implicit status call site", env)

    # Regression: retaining the central prohibition/link cannot hide a widened
    # execution boundary on any amended consuming status document. No runtime runs.
    def test_cross_document_status_boundary_regression(self):
        clauses = {
            "protocol/environments.md": (
                "Adopting readiness status MUST execute\nno agent binary, including `--version` and `auth status`;",
                "Adopting readiness status MAY execute\nan agent binary for `auth status`;"),
            "protocol/login-readiness.md": (
                "Status MUST NOT invoke an agent executable,",
                "Status MAY invoke an agent executable for auth status; it MUST NOT"),
            "cli/curator.md": (
                "Adopting status invokes no agent binary, including\nversion probes and auth status;",
                "Adopting status permits auth status; it invokes no agent binary for\nversion probes;"),
            "profiles/manager.md": (
                "execute no agent binary, including version probes and auth status.",
                "may execute auth status, but execute no agent binary for version probes."),
        }
        try:
            validate.validate_rc7_carriers()
        except validate.ValidationFailure as exc:
            self.fail(str(exc))
        original = Path.read_text
        for document, (prohibition, permission) in clauses.items():
            path = ROOT / document
            before = path.read_bytes()
            self.assertEqual(before.decode().count(prohibition), 1)

            def narrowed(target, *args, **kwargs):
                text = original(target, *args, **kwargs)
                return text.replace(prohibition, permission) if target == path else text

            with self.subTest(document=document), patch.object(Path, "read_text", new=narrowed):
                with self.assertRaisesRegex(validate.ValidationFailure,
                                            "incoherent status execution boundary: " + document):
                    validate.validate_rc7_carriers()
            self.assertEqual(path.read_bytes(), before, "publication checking must not write documents")

    # Both native projection availability and nonempty refusal are explicit;
    # full launch delivery/login cannot downgrade to shell or an old consumer.
    def test_renderer_transition_and_cli_published(self):
        publication = (ROOT / "protocol/rc7-carriers.md").read_text()
        for clause in (
            "Nonempty Codex settings refuse with `codex_settings_unsupported`, zero output",
            "Existing environment-only projection remains available",
            "Direct structured login consumes typed policy without evaluating shell output",
            "Strict status --check and prepare require every participant current and present",
            "`env login <env-id> [--profile <name>]`",
            "`profile prepare <source-or-name> [--non-interactive]`",
            "Preparation uses install's\nexplicit source grammar and default naming",
        ):
            self.assertIn(clause, publication)

    # Both supported/native projection and nonempty/unsupported refusals have
    # machine-readable requirements. A success expectation on env/file is
    # rejected with the exact named case; no real renderer executes here.
    def test_delivery_vectors_refuse_partial_or_dropped_transport(self):
        carriers.check_delivery_vectors(ROOT, validate.load_json)
        original = validate.load_json

        def invalid_expectation(path):
            value = original(path)
            if path == CORPUS / "delivery-vectors.json":
                case = next(c for c in value if c["name"] == "env-file-supported")
                case["expected"]["usable_output"] = True
                case["expected"]["diagnostic"] = None
            return value

        with self.assertRaisesRegex(carriers.ContractError,
                                    "delivery expectation differs: env-file-supported"):
            carriers.check_delivery_vectors(ROOT, invalid_expectation)


if __name__ == "__main__":
    unittest.main()
