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
        cls.cases = {c['id']: c for c in json.loads((m.ROOT/'conformance/skillfile-mcp-v1/cases.json').read_text(encoding="utf-8"))}

    # Claim: the checked-in registry loads UTF-8 schemas even when omitted text encodings default to cp1252.
    # The unencoded read is an instrument control: these schema bytes must fail under that default.
    def test_registry_scan_with_cp1252_default(self):
        original_read_text = Path.read_text
        default_reads = []
        schema_path = m.ROOT/'schemas/project-context-leaf1-v1/common.schema.json'

        def cp1252_default(path, encoding=None, errors=None):
            if encoding is None:
                default_reads.append(path)
                encoding = 'cp1252'
            return original_read_text(path, encoding=encoding, errors=errors)

        m.registry.cache_clear()
        self.addCleanup(m.registry.cache_clear)
        with patch.object(Path, 'read_text', cp1252_default):
            with self.assertRaises(UnicodeDecodeError):
                schema_path.read_text()
            catalog = m.registry()
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            self.assertEqual(catalog.contents(schema['$id']), m.exact_patterns(schema))
        self.assertEqual(default_reads, [schema_path])

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
        schema = json.loads((m.ROOT/'schemas/skillfile-sources-v1/skillfile-v2.schema.json').read_text(encoding="utf-8"))
        reader = Draft202012Validator(schema, registry=m.registry())
        checked = 0
        for path in root.rglob('*.json'):
            if 'skillfile-v2' not in path.parts:
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
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
            reader = Draft202012Validator(json.loads((m.ROOT/relative).read_text(encoding="utf-8")), registry=m.registry())
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
            cases=json.loads((original/'cases.json').read_text(encoding="utf-8"))
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


    # Claim R1–R4: reviewer witnesses fail for the named contract, valid neighbors pass,
    # and removing each actual gate produces its intended corpus verdict mismatch.
    # Limits: synthetic selection/source facts are not external snapshot attestations.
    def test_review_regressions_and_controls(self):
        controls = []
        for field in ['command', 'args', 'url']:
            for prefix in ['package-byte-', 'lock-byte-']:
                controls.append(('package_byte_bounds', prefix+field+'-over',
                                 prefix+field+'-within', self.narrowed(
                                     'package_byte_bounds',
                                     {'url': "len(server['url'].encode('utf-8')) <= 4096",
                                      'command': "len(server['command'].encode('utf-8')) <= 255",
                                      'args': "len(arg.encode('utf-8')) <= 8192"}[field],
                                     {'url': "len(server['url'].encode('utf-8')) <= 4098",
                                      'command': "len(server['command'].encode('utf-8')) <= 256",
                                      'args': "len(arg.encode('utf-8')) <= 8194"}[field])))
            m.check_case(self.cases['inline-scalar-'+field])
        for selector in ['revision', 'range']:
            controls.append(('selection_matches', 'lock-selector-'+selector+'-mismatch',
                             'lock-selector-'+selector+'-match', self.narrowed(
                                 'selection_matches',
                                 "if 'revision' in selector and selector['revision'] != resolved['commit']:"
                                 if selector == 'revision' else
                                 "if version is None or not validate.range_satisfies(validate.range_parse(selector['range']), version):",
                                 'if False:')))
        controls.append(('strict_integer', 'ccj1-negative-zero', 'ccj1-zero', int))
        controls.append(('strict_integer', 'ccj1-nested-negative-zero', 'ccj1-negative', int))
        for function, witness, sibling, replacement in controls:
            with self.subTest(gate=function, witness=witness):
                m.check_case(self.cases[witness]); m.check_case(self.cases[sibling])
                with patch.object(m, function, side_effect=replacement) as applied:
                    m.check_case(self.cases[sibling])
                    # An unrelated refusal still holds under each narrowing plant.
                    m.check_case(self.cases['allowlist-denied'])
                    with self.assertRaisesRegex(ValueError, 'MCP (?:verdict|carrier) mismatch: '+witness+'$'):
                        m.check_case(self.cases[witness])
                    self.assertGreater(applied.call_count, 0)
        gates = [
            ("if facts.get('source_allowlist_empty', False):", 'source_allowlist_empty'),
            ("if resolved.get('signed', True) is not True:", 'context_source_unsigned'),
            ("if resolved.get('signers_present', True) is not True:", 'context_source_signers_missing'),
            ("if resolved.get('version_matches', True) is not True:", 'context_version_mismatch'),
        ]
        for old, code in gates:
            witness = 'source-gate-'+code
            m.check_case(self.cases[witness]); m.check_case(self.cases['package-valid'])
            narrowed = self.narrowed('evaluate', old, 'if False:')
            with self.subTest(gate=code), patch.object(m, 'evaluate', side_effect=narrowed):
                m.check_case(self.cases['package-valid'])
                with self.assertRaisesRegex(ValueError, 'MCP verdict mismatch: '+witness+'$'):
                    m.check_case(self.cases[witness])
            # Mutate the actual schema enum, not a simulated schema verdict.
            schema = json.loads((m.ROOT/'schemas/skillfile-mcp-v1/mcp-plan-v1.schema.json').read_text(encoding="utf-8"))
            for remove in [True, False]:
                mutated = copy.deepcopy(schema)
                enum = mutated['properties']['rows']['items']['properties']['code']['enum']
                if remove:
                    enum.remove(code)
                else:
                    enum.append(code+'_unknown')
                reader = Draft202012Validator(mutated, registry=m.registry())
                original = m.schema_valid
                def changed_enum(name, value, root=m.ROOT):
                    return reader.is_valid(value) if name == 'mcp-plan-v1' else original(name, value, root)
                suffix = 'valid' if remove else 'unknown'
                witness = 'plan-source-'+code+'-'+suffix
                m.check_case(self.cases[witness])
                with self.subTest(code=code, enum_removal=remove), patch.object(m, 'schema_valid', side_effect=changed_enum):
                    m.check_case(self.cases['plan-valid'])
                    with self.assertRaisesRegex(ValueError, 'MCP carrier mismatch: '+witness+'$'):
                        m.check_case(self.cases[witness])

    # Inherited whole-string patterns reject final LF at the stage-A schema
    # boundary. Every field has a passing sibling, a field-specific guard plant
    # admitting its LF witness, and an unrelated unknown-field rejection.
    # No released schema bytes or semantic/hash checks are bypassed in product.
    def test_inherited_pattern_final_lf_controls(self):
        from referencing import Resource
        lock = copy.deepcopy(self.cases['lock-valid']['instance'])
        plan = copy.deepcopy(self.cases['plan-valid']['instance'])
        common = 'v1/common'
        agent = 'v1/agent-mcp-v1'
        cases = [
            ('skillfile-v3', {'schema_version':3,'skills':[],'agents':['sample']}, ['agents',0], common, ['$defs','identifier','allOf',0,'pattern']),
            ('declaration-v1', {'server':{'transport':'stdio','command':'sample-tool','args':[]}}, ['server','command'], agent, ['$defs','bareCommand','pattern']),
            ('declaration-v1', {'server':{'transport':'stdio','command':'sample-tool','args':[],'env_names':['SAMPLE_A']}}, ['server','env_names',0], common, ['$defs','identifier','allOf',0,'pattern']),
            ('declaration-v1', {'server':{'transport':'http','url':'https://example.invalid/mcp'}}, ['server','url'], agent, ['$defs','httpsUrl','pattern']),
            ('declaration-v1', {'package':{'git':'https://example.invalid/repo.git','revision':'a'*40}}, ['package','revision'], common, ['$defs','commit','pattern']),
            ('declaration-v1', {'package':{'git':'https://example.invalid/repo.git','tag':'v1.2.3','directory':'mcp'}}, ['package','directory'], common, ['$defs','portablePath','pattern']),
            ('skillfile-v3', {'schema_version':3,'skills':[],'locale':'en-US'}, ['locale'], common, ['$defs','locale','pattern']),
            ('declaration-v1', {'package':{'git':'https://example.invalid/repo.git','range':'^1.2.3'}}, ['package','range'], 'v1/agent-context-v1', ['$defs','range','pattern']),
            ('mcp-lock-v1', lock, ['entries',0,'resolved','version'], 'v1/agent-context-v1', ['$defs','packageVersion','pattern']),
            ('mcp-lock-v1', lock, ['entries',0,'resolved','commit'], common, ['$defs','commit','pattern']),
            ('mcp-plan-v1', plan, ['manifest_sha256'], common, ['$defs','sha256','pattern']),
        ]
        catalog = m.registry()
        for name, sibling, path, schema_name, pattern_path in cases:
            with self.subTest(schema=name, path=path):
                self.assertTrue(m.schema_valid(name, sibling))
                witness = copy.deepcopy(sibling)
                node = witness
                for key in path[:-1]: node = node[key]
                node[path[-1]] += '\n'
                self.assertFalse(m.schema_valid(name, witness))
                uri = 'https://relux-works.github.io/curator-spec/schemas/'+schema_name+'.schema.json'
                changed = copy.deepcopy(catalog.contents(uri))
                node = changed
                for key in pattern_path[:-1]: node = node[key]
                guarded = node[pattern_path[-1]]
                self.assertTrue(guarded.endswith(r'(?![\s\S])'))
                node[pattern_path[-1]] = guarded[:-len(r'(?![\s\S])')]
                narrowed = catalog.with_resource(uri,Resource.from_contents(changed))
                with patch.object(m,'registry',return_value=narrowed):
                    self.assertTrue(m.schema_valid(name,sibling))
                    self.assertTrue(m.schema_valid(name,witness))
                    unknown = copy.deepcopy(sibling); unknown['unknown_field'] = True
                    self.assertFalse(m.schema_valid(name,unknown))

    # Claim R5: the released full-document CCJ-1 identity includes every parsed member
    # (even sig), ignores whitespace/key order, and changes after a semantic edit.
    def test_manifest_ccj1_identity_regression(self):
        import hashlib
        raw = '{"schema_version":3,"skills":[],"sig":"data"}'
        variant = ' { "sig": "data", "skills": [], "schema_version": 3 }\n'
        expected = 'sha256:'+hashlib.sha256(b'{"schema_version":3,"sig":"data","skills":[]}').hexdigest()
        def check():
            self.assertEqual(m.digest(m.strict_load(raw)), expected)
            self.assertEqual(m.digest(m.strict_load(variant)), expected)
            self.assertNotEqual(m.digest(m.strict_load(raw.replace('data', 'edit'))), expected)
        check()
        # Canonicalizing without key sorting is the bounded faulty instrument.
        narrowed = self.narrowed('canonical', 'sort_keys=True', 'sort_keys=False')
        with patch.object(m, 'canonical', side_effect=narrowed):
            with self.assertRaises(AssertionError):
                check()


    # R6: all seven reviewer carriers reject terminal LF after independently
    # rehashing enclosing identities. Removing only the relevant private schema
    # guard admits the named witness; valid siblings and unknown-field closure hold.
    def test_r3_rehashed_carrier_lf_controls(self):
        from referencing import Resource
        controls = [
            ('version-lf', 'v1/agent-context-v1', 'packageVersion'),
            ('prerelease-lf', 'v1/agent-context-v1', 'packageVersion'),
            ('lock-commit-lf', 'v1/common', 'commit'),
            ('lock-content_sha256-lf', 'v1/common', 'sha256'),
            ('mcp-lock-v1-manifest_sha256-lf', 'v1/common', 'sha256'),
            ('mcp-plan-v1-manifest_sha256-lf', 'v1/common', 'sha256'),
            ('mcp-approval-v1-server_sha256-lf', 'v1/common', 'sha256'),
        ]
        catalog = m.registry()
        for label, schema, definition in controls:
            with self.subTest(witness=label):
                sibling = self.cases['r3-'+label+'-valid']
                witness = self.cases['r3-'+label+'-invalid']
                m.check_case(sibling); m.check_case(witness)
                uri = 'https://relux-works.github.io/curator-spec/schemas/'+schema+'.schema.json'
                document = copy.deepcopy(catalog.contents(uri))
                node = document['$defs'][definition]
                guard = r'(?![\s\S])'
                self.assertTrue(node['pattern'].endswith(guard))
                node['pattern'] = node['pattern'][:-len(guard)]
                narrowed = catalog.with_resource(uri, Resource.from_contents(document))
                with patch.object(m, 'registry', return_value=narrowed):
                    m.check_case(sibling)
                    unknown = copy.deepcopy(sibling['instance']); unknown['unknown_field'] = True
                    self.assertFalse(m.carrier_valid(sibling['schema'], unknown))
                    with self.assertRaisesRegex(ValueError, '^MCP carrier mismatch: '+witness['id']+'$'):
                        m.check_case(witness)

    # R7: both intermediate dot/space variants refuse in rehashed locks and
    # plans, and in package admission. Narrowing only the shared component-end
    # rule admits each violation; traversal rejection and valid paths remain.
    def test_r3_portable_component_controls(self):
        import ccj1_grammar as grammar
        source = inspect.getsource(grammar.portable_path)
        anchor = "component.endswith(('.', ' '))"
        self.assertEqual(source.count(anchor), 1)
        namespace = dict(vars(grammar))
        exec(source.replace(anchor, 'False'), namespace)
        for kind in ('mcp-lock-v1', 'mcp-plan-v1', 'package'):
            for ending in ('dot', 'space'):
                label = 'r3-'+kind+'-component-'+ending
                sibling = self.cases[label+'-valid']; witness = self.cases[label+'-invalid']
                with self.subTest(witness=label):
                    m.check_case(sibling); m.check_case(witness)
                    with patch.object(m, 'portable_path', side_effect=namespace['portable_path']) as plant:
                        m.check_case(sibling)
                        self.assertFalse(m.package_valid({'git':'https://example.invalid/repo.git', 'tag':'v1.2.3', 'directory':'pkg/../root'}))
                        with self.assertRaisesRegex(ValueError, '^MCP (?:carrier|verdict) mismatch: '+witness['id']+'$'):
                            m.check_case(witness)
                        self.assertGreater(plant.call_count, 0)

    # R8: each signed text/bytes token receives mcp_declaration_invalid without
    # attempting oversized int conversion; safe signed extrema remain accepted.
    # Actual gate plants separately demonstrate pre-conversion detection and the
    # typed mapping (an untyped ValueError is precisely the regression under test).
    def test_r3_oversized_integer_controls(self):
        import ccj1_grammar as grammar
        source = inspect.getsource(grammar.integer)
        self.assertEqual(source.count('len(digits) > 16'), 1)
        for sign in ('positive', 'negative'):
            for encoding in ('text', 'bytes'):
                label = 'r3-integer-'+sign+'-'+encoding
                sibling = self.cases[label+'-valid']; witness = self.cases[label+'-invalid']
                overlong = []
                def conversion(token):
                    if len(token.lstrip('-')) > 16:
                        overlong.append(len(token.lstrip('-')))
                        # The instrument never converts the hostile token or changes
                        # the interpreter's digit limit; this is a known gate plant.
                        raise ValueError('oversized conversion attempted')
                    return int(token)
                def check_before_conversion():
                    m.check_case(sibling); m.check_case(witness)
                    self.assertEqual(overlong, [], 'oversized conversion attempted')
                with self.subTest(witness=label):
                    with patch.object(grammar, 'int', side_effect=conversion, create=True):
                        check_before_conversion()
                    namespace = dict(vars(grammar)); namespace['int'] = conversion
                    exec(source.replace('len(digits) > 16', 'False'), namespace)
                    with patch.object(m, 'strict_integer', side_effect=namespace['integer']):
                        with self.assertRaisesRegex(AssertionError, 'oversized conversion attempted'):
                            check_before_conversion()
                    self.assertEqual(overlong, [5000])
                    # Removing only the ValueError mapping leaks the helper's known
                    # lexical refusal, so the expected typed-verdict claim must fail.
                    narrowed = self.narrowed('strict_load',
                        'except (ValueError, UnicodeError, TypeError):',
                        'except (UnicodeError, TypeError):')
                    def typed_claim(case):
                        try:
                            m.check_case(case)
                        except m.Refusal:
                            raise
                        except ValueError as error:
                            self.assertEqual(str(error), 'CCJ-1 integer length')
                            self.fail('untyped ValueError instead of declaration refusal')
                    with patch.object(m, 'strict_load', side_effect=narrowed):
                        m.check_case(sibling)
                        with self.assertRaisesRegex(AssertionError, 'untyped ValueError instead of declaration refusal'):
                            typed_claim(witness)
                # Verify the fixture actually uses the requested byte/text boundary.
                original = m.evaluate
                observed = []
                def capture(raw, *args):
                    observed.append(type(raw)); return original(raw, *args)
                with patch.object(m, 'evaluate', side_effect=capture):
                    m.check_case(witness)
                self.assertEqual(observed, [bytes if encoding == 'bytes' else str])

    # The real publication dispatcher validates every added regression; a wrong
    # expected verdict for each defect class fails with its exact case diagnostic.
    # Inputs are replaced in memory only, leaving the checked-out corpus untouched.
    def test_r3_publication_regressions_and_controls(self):
        validate.validate_skillfile_mcp()
        corpus = m.ROOT/'conformance/skillfile-mcp-v1/cases.json'
        original = Path.read_bytes
        for name in ('r3-version-lf-invalid', 'r3-mcp-lock-v1-component-dot-invalid',
                     'r3-integer-positive-text-invalid'):
            planted = copy.deepcopy(list(self.cases.values()))
            witness = next(case for case in planted if case['id'] == name)
            if witness['kind'] == 'carrier': witness['valid'] = True
            else: witness['expected']['code'] = None
            def read_bytes(path):
                return json.dumps(planted).encode() if path == corpus else original(path)
            with self.subTest(witness=name), patch.object(Path, 'read_bytes', read_bytes):
                with self.assertRaisesRegex(validate.ValidationFailure, 'MCP (?:carrier|verdict) mismatch: '+name+'$'):
                    validate.validate_skillfile_mcp()


if __name__ == '__main__':
    unittest.main()
