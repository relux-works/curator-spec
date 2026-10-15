from __future__ import annotations

import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import login_readiness
from test_validate import validate


class LoginReadinessTests(unittest.TestCase):
    def setUp(self):
        self.schemas = {p.name: json.loads(p.read_text()) for p in
                        (validate.ROOT / 'schemas/login-readiness-v1').glob('*.json')}
        self.cases = json.loads((validate.ROOT / 'conformance/login-readiness-v1/index.json').read_text())

    # The real schema entry validates every indexed positive and negative, not native probes.
    def test_all_published_cases(self):
        total, negatives = login_readiness.validate(validate.ROOT)
        self.assertEqual(total, len(self.cases))
        self.assertGreater(negatives, 0)

    # Narrowing closure to allow one secret field must be caught by invalid-secret.
    def test_detail_secret_exception_is_killed(self):
        self.schemas['login-row-v1.schema.json']['properties']['login_detail']['properties']['token'] = {'type': 'string'}
        with self.assertRaisesRegex(login_readiness.ContractError, 'invalid-secret:'):
            login_readiness.validate(validate.ROOT, schemas=self.schemas)

    # Narrowing one adapter's mapping refusal must be caught; native Pi remains a control.
    def test_pi_only_file_exception_is_killed(self):
        policy = self.schemas['store-projection-v1.schema.json']
        arm = copy.deepcopy(policy['oneOf'][3])
        arm['properties']['environment'] = {'const': 'pi'}
        arm['properties']['env'] = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
        policy['oneOf'].append(arm)
        with self.assertRaisesRegex(login_readiness.ContractError, 'invalid-file-pi:'):
            login_readiness.validate(validate.ROOT, schemas=self.schemas)

    # Accepting only one wrong session cannot pass the caller-scoped row corpus.
    def test_machine_session_exception_is_killed(self):
        self.schemas['login-row-v1.schema.json']['properties']['login_detail']['properties']['session'] = {'enum': ['caller', 'machine']}
        with self.assertRaisesRegex(login_readiness.ContractError, 'invalid-session:'):
            login_readiness.validate(validate.ROOT, schemas=self.schemas)

    # Keeping override syntax but accepting a contradictory file mapping must fail.
    def test_codex_file_keyring_mismatch_is_killed(self):
        policy = self.schemas['store-projection-v1.schema.json']
        policy['oneOf'][1]['properties']['credential_store']['properties']['config_overrides']['properties']['cli_auth_credentials_store'] = {'enum': ['file', 'keyring']}
        with self.assertRaisesRegex(login_readiness.ContractError, 'invalid-codex-override:'):
            login_readiness.validate(validate.ROOT, schemas=self.schemas)

    # A metadata read failure cannot be relabelled as successful absence by the row grammar.
    def test_absent_metadata_failure_reason_is_rejected(self):
        row = json.loads((validate.ROOT / 'conformance/login-readiness-v1/schema-cases/absent-row.json').read_text())
        row['login_detail']['reason'] = 'metadata-unavailable'
        from jsonschema import Draft202012Validator
        registry, _ = validate.schema_registry()
        validator = Draft202012Validator(self.schemas['login-row-v1.schema.json'], registry=registry)
        self.assertFalse(validator.is_valid(row))

    # Removing a refusal witness from the index cannot silently reduce measured coverage.
    def test_unindexed_case_is_rejected(self):
        with self.assertRaisesRegex(login_readiness.ContractError, 'inventory'):
            login_readiness.validate(validate.ROOT, cases=self.cases[:-1])

    # Production dispatch must return 1 on a malformed readiness corpus.
    def test_main_calls_login_readiness_gate(self):
        with contextlib.ExitStack() as stack:
            for name in vars(validate):
                if name.startswith('validate_') and name not in {'validate_login_readiness', 'validate_wire_semantics'}:
                    stack.enter_context(patch.object(validate, name, return_value=None))
            stack.enter_context(patch.object(login_readiness, 'validate', side_effect=login_readiness.ContractError('control violation')))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            self.assertEqual(validate.main(), 1)

    # All released full-fragment readers reject the new token and new member.
    def test_old_fragment_readers_reject_policy_and_unknown_revision(self):
        from jsonschema import Draft202012Validator
        registry, _ = validate.schema_registry()
        for version in (1, 2, 3):
            schema = validate.load_json(validate.SCHEMAS / f'launch-env-fragment-v{version}.schema.json')
            instance = {'fragment': f'launch-env-fragment-v{version}', 'environment': 'codex_cli',
                        'profile': {'name': 'example', 'lock_sha256': '0' * 64},
                        'precedence': {'winner': 'higher-weight', 'placement': 'winner-last'},
                        'env': {'CODEX_HOME': '/managed/example/codex'}}
            if version >= 2:
                instance['permissions'] = {'mode': 'native', 'locked': False, 'source': 'default'}
            checker = Draft202012Validator(schema, registry=registry)
            with self.subTest(version=version):
                self.assertTrue(checker.is_valid(instance))
                extra = copy.deepcopy(instance)
                extra['credential_store'] = {'selection': 'native'}
                self.assertFalse(checker.is_valid(extra))
                extra = copy.deepcopy(instance)
                extra['fragment'] = 'unsupported-login-readiness-revision'
                self.assertFalse(checker.is_valid(extra))
                extra = copy.deepcopy(instance)
                extra['env']['TBH_CREDENTIAL_BACKEND'] = 'file'
                self.assertFalse(checker.is_valid(extra))
