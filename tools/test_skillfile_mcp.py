"""Executable stage-A spec claims and bounded narrowing controls, no native writer qualification."""
import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
import skillfile_mcp as m
import validate


class StageATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c['id']: c for c in json.loads((m.ROOT/'conformance/skillfile-mcp-v1/cases.json').read_text())}

    # Claim: the production spec corpus agrees with every independently stated verdict, not just any error.
    def test_corpus(self):
        total, negatives = m.check_corpus()
        self.assertEqual(total, len(self.cases))
        self.assertGreater(negatives, 0)
        self.assertLess(negatives, total)

    # Claim: each failed planning case preserves supplied observations and reports no model mutation.
    # Limit: this is data-model immutability, not proof of a native filesystem transaction.
    def test_no_fact_mutation_or_secret_diagnostic(self):
        for case in self.cases.values():
            if case['kind'] != 'planning':
                continue
            with self.subTest(case=case['id']):
                original = copy.deepcopy(case['facts'])
                result = m.evaluate(case['raw'], case['facts'])
                self.assertEqual(case['facts'], original)
                self.assertIs(result['mutated'], False)
                rendered = json.dumps(result)
                self.assertNotIn('AKIAJ7Q3ZX9PLM2RT5WQ', rendered)

    # Claim: absent package manifest has a typed refusal and no fabricated pair target, rather than a reporting crash.
    def test_missing_manifest_reporting_regression(self):
        case = self.cases['manifest-missing']
        result = m.evaluate(case['raw'], case['facts'])
        self.assertEqual(result, dict(code='mcp_declaration_invalid', rows=[], mutated=False))
        m.check_case(self.cases['package-valid'])

    # Claim: schema 3 retains all checked-in schema-2 structural instances in both validity directions.
    # The only intended asymmetry is the new version and optional MCP field, tested independently.
    def test_schema2_inheritance(self):
        root = m.ROOT/'conformance/skillfile-sources-v1/schema-cases'
        schema = json.loads((m.ROOT/'schemas/skillfile-sources-v1/skillfile-v2.schema.json').read_text())
        reader = Draft202012Validator(schema, registry=m.registry())
        checked = 0
        for path in root.rglob('*.json'):
            if 'skillfile-v2' not in path.parts:
                continue
            value = json.loads(path.read_text())
            if not isinstance(value, dict) or value.get('schema_version') != 2:
                continue
            expected = reader.is_valid(value)
            value['schema_version'] = 3
            self.assertEqual(m.schema_valid('skillfile-v3', value), expected, str(path.relative_to(root)))
            checked += 1
        self.assertGreater(checked, 10)

    # Claim: released readers keep rejecting MCP additions; unknown versions are not silently dispatched to schema 2.
    def test_old_schemas_closed(self):
        for version, relative in [(1,'schemas/v1/skillfile-v1.schema.json'),(2,'schemas/skillfile-sources-v1/skillfile-v2.schema.json')]:
            reader = Draft202012Validator(json.loads((m.ROOT/relative).read_text()), registry=m.registry())
            self.assertTrue(reader.is_valid({'schema_version':version,'skills':[]}))
            self.assertFalse(reader.is_valid({'schema_version':version,'skills':[],'mcp_servers':{}}))
            self.assertFalse(reader.is_valid({'schema_version':3,'skills':[]}))

    # Claim: normalization equates shorthand/key/set order but preserves absent selectors, arguments and scalar spelling.
    def test_distinct_digests(self):
        url = 'https://docs.example.invalid/mcp'
        shorthand = m.normalize_declaration(url)
        expanded = m.normalize_declaration({'server':{'url':url,'transport':'http','env_names':[]},'install':{}})
        self.assertEqual(shorthand, expanded)
        self.assertEqual(m.digest(shorthand),m.digest(expanded))
        a = {'transport':'stdio','command':'tools','args':['x','y'],'env_names':['B','A'],'environments':['muse','claude_code']}
        b = dict(a,env_names=['A','B'],environments=['claude_code','muse'])
        expected = {'transport':'stdio','command':'tools','args':['x','y'],'env_names':['A','B'],'environments':['claude_code','muse']}
        self.assertEqual(m.normalize_server(a), expected)
        self.assertEqual(m.digest(m.normalize_server(a)),m.digest(m.normalize_server(b)))
        for changed in [dict(a,args=['y','x']),dict(a,env_names=['A']),dict(a,environments=['muse']),dict(a,command='Tools')]:
            self.assertNotEqual(m.digest(m.normalize_server(a)),m.digest(m.normalize_server(changed)))
        self.assertNotEqual(m.digest(m.normalize_server({'transport':'http','url':url})),m.digest(m.normalize_server({'transport':'http','url':url,'environments':['claude_code','codex_cli','muse']})))
        original = m.normalize_declaration({'server':a})
        with_install = m.normalize_declaration({'server':a,'install':{'sig':'data'}})
        self.assertNotEqual(m.digest(original),m.digest(with_install))
        self.assertEqual(m.digest(original['server']),m.digest(with_install['server']))
        self.assertEqual(m.canonical({'b':1,'a':2}),b'{"a":2,"b":1}')
        self.assertFalse(m.canonical(original).endswith(b'\n'))
        self.assertNotEqual(m.digest({'url':url}),m.digest({'url':url.upper()}))
        self.assertNotEqual(m.digest({'s':'é'}),m.digest({'s':'e\u0301'}))
        one={'schema_version':3,'skills':[],'mcp_servers':{'docs':url}}
        two=dict(one,mcp_servers={'docs':{'server':{'transport':'http','url':url}}})
        self.assertNotEqual(m.digest(one),m.digest(two))
        self.assertEqual(m.digest(one),m.digest(json.loads(json.dumps(one,indent=2))))

    # Claim: strict byte parsing catches invalid UTF-8 and escaped surrogate scalars without echoing raw bytes.
    def test_strict_bytes(self):
        for raw in [b'\xff',b'{"x":"\\ud800"}',b'{"x":9007199254740992}',b'{"x":1.2}',b'{"x":Infinity}']:
            with self.subTest(raw=repr(raw)), self.assertRaisesRegex(m.Refusal,'^mcp_declaration_invalid$'):
                m.strict_load(raw)
        self.assertEqual(m.strict_load(b'{"x":9007199254740991}'),{'x':9007199254740991})

    # Claim: a later invalid declaration does not suppress an independently determinable valid package pair.
    def test_partial_enumeration(self):
        case = self.cases['package-valid'];manifest=json.loads(case['raw']);manifest['mcp_servers']['bad']=None
        result=m.evaluate(json.dumps(manifest),case['facts'])
        self.assertEqual(result['code'],'mcp_declaration_invalid')
        self.assertEqual(len(result['rows']),2)
        self.assertTrue(all(r['outcome']=='refused' and r['code']=='mcp_declaration_invalid' for r in result['rows']))

    # Claim: production dispatch surfaces a failed MCP corpus, instead of dropping this extension from validate.py.
    def test_production_dispatch(self):
        with patch.object(m,'check_corpus',side_effect=ValueError('planted MCP contract violation')) as planted:
            with self.assertRaisesRegex(validate.ValidationFailure,'planted MCP contract violation'):
                validate.validate_skillfile_mcp()
            planted.assert_called_once_with(validate.ROOT)
        validate.validate_skillfile_mcp()

    # Claim: removing a required witness from data alone fails the exact coverage inventory.
    def test_missing_witness(self):
        with tempfile.TemporaryDirectory(prefix='mcp-corpus-') as directory:
            root=Path(directory);corpus=root/'conformance/skillfile-mcp-v1';corpus.mkdir(parents=True)
            original=m.ROOT/'conformance/skillfile-mcp-v1'
            cases=json.loads((original/'cases.json').read_text())
            (corpus/'cases.json').write_text(json.dumps(cases[1:]))
            (corpus/'coverage.json').write_bytes((original/'coverage.json').read_bytes())
            with self.assertRaisesRegex(ValueError,'MCP case inventory mismatch'):
                m.check_corpus(root)

    # Claim: coherently deleting a named refusal from data and inventory still fails required code coverage.
    def test_missing_refusal_coverage(self):
        with tempfile.TemporaryDirectory(prefix='mcp-coverage-') as directory:
            root=Path(directory);corpus=root/'conformance/skillfile-mcp-v1';corpus.mkdir(parents=True)
            cases=[c for c in self.cases.values() if c['id']!='allowlist-empty-hardened']
            (corpus/'cases.json').write_text(json.dumps(cases))
            (corpus/'coverage.json').write_text(json.dumps({'cases':[c['id'] for c in cases]}))
            with self.assertRaisesRegex(ValueError,'MCP refusal coverage mismatch'):
                m.check_corpus(root)

    # Claim: this specification oracle uses none of these execution/network APIs for a valid package plan.
    # Limit: this does not qualify a manager; the bounded tripwire control proves the patched instrument fires.
    def test_oracle_no_execution(self):
        with patch('subprocess.run',side_effect=AssertionError('execution tripwire')) as run, \
             patch('subprocess.Popen',side_effect=AssertionError('spawn tripwire')) as popen, \
             patch('socket.create_connection',side_effect=AssertionError('network tripwire')) as connect:
            m.check_case(self.cases['package-valid'])
            run.assert_not_called();popen.assert_not_called();connect.assert_not_called()
            with self.assertRaisesRegex(AssertionError,'^execution tripwire$'):
                __import__('subprocess').run(['inert-control'])

    def narrowed(self, function, old, new):
        source=inspect.getsource(getattr(m,function))
        self.assertEqual(source.count(old),1,(function,old))
        namespace=dict(vars(m));exec(compile(source.replace(old,new),'<bounded-mcp-mutant>','exec'),namespace)
        return namespace[function]

    # Claim: actual checker controls reject known gates narrowed one at a time for the named intended verdict.
    # Neither a crash nor an unapplied mutation counts as a killed control.
    def test_narrowing_controls(self):
        normalizer=m.normalize_server
        controls=[
            ('strict_load','duplicate-key',lambda *a:json.loads(*a)),
            ('url_valid','url-format',lambda _:True),
            ('runtime_pin','npx-unpinned',lambda *a:True),
            ('runtime_pin','uvx-unpinned',lambda *a:True),
            ('audit_clear','secret-shorthand',lambda *a:True),
            ('stage_a','admission-inline',lambda _:True),
            ('allowed','allowlist-denied',lambda *a:True),
            ('ownership_allowed','foreign-entry',lambda _:True),
            ('policy_allowed','action-no-authority',lambda *a:True),
            ('targets','absent-environment',lambda server,writable:server.get('environments',['claude_code'])),
            ('package_valid','package-traversal-git',lambda _:True),
            ('schema_valid','unknown',lambda *a:True),
            ('schema_valid','unknown-environment',lambda *a:True),
            ('normalize_server','normalize-stdio',lambda server:dict(normalizer(server),args=[])),
            ('normalize_declaration','normalize-url',lambda x:x),
        ]
        for function,witness,replacement in controls:
            with self.subTest(gate=function,witness=witness):
                m.check_case(self.cases[witness])
                with patch.object(m,function,side_effect=replacement) as applied:
                    with self.assertRaisesRegex(ValueError,'MCP verdict mismatch: '+witness+'$'):
                        m.check_case(self.cases[witness])
                    self.assertGreater(applied.call_count,0)
        mutations=[
            ('evaluate',"or facts.get('scope', 'project') != 'project'",'or False','global-upgrade'),
            ('evaluate',"or facts.get('schema3_supported', True) is not True",'or False','old-reader-upgrade'),
            ('evaluate',"if not audit_clear(package, root):",'if False:','secret-args'),
            ('evaluate',"if not audit_clear(decl, root):",'if False:','secret-install'),
            ('evaluate',"if facts.get('hardened', False):",'if False:','allowlist-empty-hardened'),
            ('evaluate',"if resolved.get('snapshot_matches', True) is not True:",'if False:','snapshot-changed'),
            ('evaluate',"if resolved.get('signer_allowed', True) is not True:",'if False:','signer-refused'),
            ('evaluate',"if facts.get('preimage_read', 'ok') != 'ok':",'if False:','unreadable-preimage'),
            ('carrier_valid',"if value[field] != digest({k:v for k,v in value.items() if k != field}):",'if False:','lock-self-hash'),
            ('carrier_valid',"if value['skills_lock']['manifest_sha256'] != value['manifest_sha256']:",'if False:','lock-manifest-mismatch'),
            ('carrier_valid',"if skill_lock['lock_sha256'] != digest({k:v for k,v in skill_lock.items() if k != 'lock_sha256'}):",'if False:','lock-skills-hash'),
            ('carrier_valid',"or resolved['server'] != normalize_server(resolved['server'])",'or False','lock-unnormalized-rehashed'),
            ('carrier_valid',"if options != sorted(set(options)):",'if False:','plan-duplicate-option'),
            ('carrier_valid',"if names != sorted(set(names)):",'if False:','lock-duplicate-name'),
            ('carrier_valid',"or entry['declaration_sha256'] != digest(model)",'or False','lock-declaration-digest'),
            ('carrier_valid',"or resolved['server_sha256'] != digest(resolved['server'])",'or False','lock-server-digest'),
            ('carrier_valid',"or resolved['source'] != identity(model['package']['git'])",'or False','lock-source-identity'),
            ('carrier_valid',"or resolved['directory'] != model['package'].get('directory')",'or False','lock-directory'),
            ('carrier_valid',"if keys != sorted(set(keys)):",'if False:','plan-duplicate-pair'),
            ('carrier_valid',"or refusals and row['outcome'] in successes",'or False','plan-refusal-partial-success'),
            ('carrier_valid',"or row['outcome'] in successes and row['path'] is None",'or False','plan-unavailable-success'),
            ('carrier_valid',"or row['outcome'] == 'skipped: unsupported' and row['path'] is not None",'or False','plan-unsupported-path'),
            ('carrier_valid',"if value['rows'] and not refusals and value['lock_sha256'] is None:",'if False:','plan-missing-lock'),
        ]
        for function,old,new,witness in mutations:
            with self.subTest(gate=function,witness=witness):
                m.check_case(self.cases[witness])
                narrowed=self.narrowed(function,old,new)
                with patch.object(m,function,side_effect=narrowed) as applied:
                    with self.assertRaisesRegex(ValueError,'MCP (?:verdict|carrier) mismatch: '+witness+'$'):
                        m.check_case(self.cases[witness])
                    self.assertGreater(applied.call_count,0)


if __name__ == '__main__':
    unittest.main()
