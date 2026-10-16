#!/usr/bin/env python3
"""Disposable T0 publication plants and narrowing controls; no real secrets."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import local_setup_token as local
import validate

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'conformance' / local.NAMESPACE / 'cases.json'

# These mutations retain the general gate and admit one forbidden subclass.
MUTANTS = [
    ('node-file-store', 'admit only node+file while still rejecting keychain', 'test_st01_authority_store_and_isolation'),
    ('repair-migration', 'admit only repair source migration, retaining resolve/start refusals', 'test_st06_native_preservation_and_explicit_adoption'),
    ('other-uid', 'ignore only executing UID while retaining host/profile binding', 'test_st07_local_binding_and_required_understanding'),
    ('stale-policy', 'ignore only policy generation, retaining source generation/ref checks', 'test_st07_local_binding_and_required_understanding'),
    ('unknown-node-branch', 'admit only future-node as a required extension branch', 'test_st07_local_binding_and_required_understanding'),
    ('nested-unknown-source', 'admit only future-node inside the plan fragment while retaining other unknown branches', 'test_st07_nested_unknown_source_diagnostic'),
    ('null-required-extension', 'admit only a null required extension by borrowing the fragment source; other malformed kinds still refuse', 'test_st07_malformed_extension_typed_refusal'),
    ('future-fragment-as-usage', 'classify only fragment v99 as usage, retaining unavailable for other unknown revisions', 'test_st07_unknown_carrier_discriminators_typed_refusal'),
    ('future-marker-as-usage', 'classify only marker v99 as usage, retaining unavailable for other unknown revisions', 'test_st07_unknown_carrier_discriminators_typed_refusal'),
    ('direct-plan-route-as-usage', 'classify only direct-only plan route as usage, retaining unavailable for other unsupported routes', 'test_st13_unsupported_plan_route_typed_refusal'),
    ('source-secret-path', 'admit only a secret_path member in the node source', 'test_st09_secret_fields_and_closed_snapshots'),
    ('source-token-field', 'admit only a token member in the node source', 'test_st09_secret_fields_and_closed_snapshots'),
    ('snapshot-source', 'admit only source projection on snapshot descriptor', 'test_st09_secret_fields_and_closed_snapshots'),
    ('direct-as-spawn', 'admit direct-only evidence as the headless route', 'test_st13_route_and_snapshot_are_not_authority'),
    ('caller-present-as-qualified', 'admit caller presence as qualification', 'test_st13_route_and_snapshot_are_not_authority'),
]


def run_plant(plant):
    original = validate.load_json
    local.check_corpus(ROOT, original, validate.validate_wire_semantics)
    selected = 'valid-node-source-v1' if plant == 'secret' else 'matching-local-tuple'

    def load(path):
        value = original(path)
        if path == CASES:
            case = next(c for c in value['cases'] if c['name'] == selected)
            if plant == 'secret':
                case['input']['token'] = 'SYNTHETIC-FORBIDDEN-CREDENTIAL'
            else:
                case['input']['plan']['required_extensions']['works.relux.curator.credential/1']['mode'] = 'future-node'
        return value

    intended = 'usage' if plant == 'secret' else local.UNAVAILABLE
    try:
        local.check_corpus(ROOT, load, validate.validate_wire_semantics)
    except local.ContractError as exc:
        if f'{selected}: expected None, got {intended};' not in str(exc):
            raise
        print(f'EXPECTED RED {plant}: {exc}')
        local.check_corpus(ROOT, original, validate.validate_wire_semantics)
        return 1
    print(f'SURVIVING PLANT {plant}: intended refusal missing')
    return 0


def run_mutants():
    from test_local_setup_token import LocalSourceTests
    original_load = validate.load_json
    survivors = []
    print('| Mutant | What the gate is narrowed to | Named failing test | Survivor bound |')
    print('|---|---|---|---|')
    for mutant, narrowing, test in MUTANTS:
        applied = False

        def load(path):
            nonlocal applied
            value = copy.deepcopy(original_load(path))
            if path.name == 'node-source-v1.schema.json' and mutant in ('source-secret-path', 'source-token-field'):
                value['properties']['secret_path' if mutant == 'source-secret-path' else 'token'] = {'type': 'string'}
                applied = True
            if path.name == 'snapshot-launch-v1.schema.json' and mutant == 'snapshot-source':
                value['properties']['credential_source'] = {'$ref': '../local-setup-token-v1/source-projection-v1.schema.json'}
                applied = True
            return value

        # Change the actual admission code in an isolated namespace. Do not
        # rewrite fixture inputs or expected verdicts to simulate a killed gate.
        source = Path(local.__file__).read_text()
        replacements = {
            'future-fragment-as-usage': (
                "if is_discriminator and token != expected:",
                "if is_discriminator and token != expected and (name, token) != ('launch-env-fragment-v6', 'launch-env-fragment-v99'):"),
            'future-marker-as-usage': (
                "if is_discriminator and token != expected:",
                "if is_discriminator and token != expected and (name, token) != ('agent-environment-marker-v6', 99):"),
            'direct-plan-route-as-usage': (
                "if isinstance(route, str) and route != 'task-board-headless-local':",
                "if isinstance(route, str) and route not in ('task-board-headless-local', 'direct-only'):"),
            'node-file-store': (
                "get('claude_code', 'native') != 'native':",
                "get('claude_code', 'native') not in ('native', 'file'):"),
            'repair-migration': (
                "value['operation'] != 'admitted-apply':",
                "value['operation'] not in ('admitted-apply', 'repair'):"),
            'other-uid': (
                "for k in ('executing_uid', 'host_ref', 'harness', 'harness_channel')",
                "for k in ('host_ref', 'harness', 'harness_channel')"),
            'stale-policy': (
                "any(binding[k] != plan[k] for k in ('source_generation', 'policy_generation'))",
                "any(binding[k] != plan[k] for k in ('source_generation',))"),
            'unknown-node-branch': (
                "        plan = value['plan']\n",
                "        value = copy.deepcopy(value)\n"
                "        extension = value['plan'].get('required_extensions', {}).get('works.relux.curator.credential/1', {})\n"
                "        if extension.get('mode') == 'future-node':\n"
                "            extension['mode'] = 'node'\n"
                "            source = value['plan']['fragment']['credential_source']['source']\n"
                "            if source.get('mode') == 'future-node':\n"
                "                source['mode'] = 'node'\n"
                "        plan = value['plan']\n"),
            'nested-unknown-source': (
                "    error = required_source_error(name, value)\n",
                "    if name == 'local-final-exec-v1':\n"
                "        value = copy.deepcopy(value)\n"
                "        source = value['fragment']['credential_source']['source']\n"
                "        if source.get('mode') == 'future-node':\n"
                "            source['mode'] = 'node'\n"
                "    error = required_source_error(name, value)\n"),
            'null-required-extension': (
                "    error = required_source_error(name, value)\n",
                "    if name == 'local-final-exec-v1' and isinstance(value, dict):\n"
                "        extensions = value.get('required_extensions')\n"
                "        if isinstance(extensions, dict) and 'works.relux.curator.credential/1' in extensions and extensions['works.relux.curator.credential/1'] is None:\n"
                "            value = copy.deepcopy(value)\n"
                "            value['required_extensions']['works.relux.curator.credential/1'] = copy.deepcopy(value['fragment']['credential_source']['source'])\n"
                "    error = required_source_error(name, value)\n"),
            'direct-as-spawn': (
                "value['route'] != 'task-board-headless-local':",
                "value['route'] not in ('task-board-headless-local', 'direct-only'):"),
            'caller-present-as-qualified': (
                "value['qualification'] != 'qualified-fixture-tuple'",
                "value['qualification'] not in ('qualified-fixture-tuple', 'source-caller-present')"),
        }
        if mutant in replacements:
            old, new = replacements[mutant]
            if source.count(old) != 1:
                raise RuntimeError('narrowing mutation target changed: ' + mutant)
            source = source.replace(old, new, 1)
            applied = True
        namespace = {'__name__': 'isolated_local_source_mutant', '__file__': local.__file__}
        exec(compile(source, local.__file__, 'exec'), namespace)
        policy = namespace['policy_error']

        with patch.object(validate, 'load_json', side_effect=load), patch.object(local, 'policy_error', side_effect=policy):
            result = unittest.TestResult()
            LocalSourceTests(test).run(result)
        killed = applied and bool(result.failures) and not result.errors and not result.skipped
        if not killed:
            survivors.append(mutant)
        print(f'| {mutant} | {narrowing} | {test if killed else "none"} | '
              f'{"none; killed" if killed else "unproven; intended assertion did not fail"} |')
    print(f'Narrowing mutants killed: {len(MUTANTS)-len(survivors)}/{len(MUTANTS)}')
    return int(bool(survivors))


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == []:
        raise SystemExit(run_mutants())
    if len(args) == 2 and args[0] == '--plant' and args[1] in ('secret', 'branch'):
        raise SystemExit(run_plant(args[1]))
    raise SystemExit('usage: check_local_setup_token_controls.py [--plant secret|branch]')
