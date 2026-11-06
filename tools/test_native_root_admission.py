"""Named review vectors and control plants; no native runtime qualification."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

import native_root_admission as proposal
import profile_command_roots as model
import generate_profile_command_roots as fixtures


class NativeRootAdmission(unittest.TestCase):
    def setUp(self):
        self.case=json.loads((model.CORPUS/'native-admission-proposal.json').read_text())
        p=self.case['policy']
        self.trusted=dict(home='/m',uid=1000,policy_revision=1,selected_revision=1,
                          request=deepcopy(self.case['acquire']),
                          **{k:deepcopy(p[k]) for k in ['manager','launcher','entry_point']})

    def test_candidate_policy_locations_and_replay(self):
        # Valid native candidate admits; each coherent mutation refuses by its
        # intended guard and leaves all input/preimage records unchanged.
        proposal.check_candidate(self.case,self.trusted)
        mutations=[
            ('candidate-schema',lambda c:c['policy']['manager'].update(path='curator')),
            ('candidate-schema',lambda c:c['policy']['entry_point'].update(legacy_excluded=False)),
            ('candidate-schema',lambda c:c['policy']['launcher'].update(capability='fragment-v4')),
            ('candidate-policy-authority',lambda c:c['policy'].update(uid=2000)),
            ('candidate-policy-authority',lambda c:c['policy'].update(revision=2)),
            ('candidate-manager',lambda c:c['policy']['manager'].update(sha256='f'*64)),
            ('candidate-selected-lock',lambda c:c['policy']['profiles'][0].update(lock_sha256='f'*64)),
            ('candidate-profile-duplicate',lambda c:c['policy']['profiles'].append(dict(c['policy']['profiles'][0],lock_sha256='f'*64))),
            ('candidate-selection',lambda c:c['selected'].update(revision=2)),
            ('candidate-generation-location',lambda c:c['generation'].update(inventory='/outside/inventory.json')),
            ('session-request-conflict',lambda c:c['acquire'].update(request_id='f'*64)),
            ('candidate-issued-supervisor_instance',lambda c:c['replay']['pin'].update(supervisor_instance='f'*64)),
        ]
        for reason,change in mutations:
            with self.subTest(reason=reason):
                bad=deepcopy(self.case);change(bad);before=deepcopy(bad)
                with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):
                    proposal.check_candidate(bad,self.trusted)
                self.assertEqual(bad,before,reason)
        replay=self.case['replay'];before=deepcopy(replay)
        self.assertEqual(proposal.replay_acquire(replay,self.case['acquire']),replay['pin'])
        bad=deepcopy(self.case['acquire']);bad['binding']['generation']='f'*64
        with self.assertRaisesRegex(model.Refusal,'^session-request-conflict$'):
            proposal.replay_acquire(replay,bad)
        self.assertEqual(replay,before)

    def test_conditional_joint_carrier(self):
        # Proposed pairing preserves rc7 Codex ownership; neither/paired pass,
        # half pairs, unknowns and missing typed settings refuse. Wire stays closed.
        candidate=proposal.joint_candidate()
        core=json.loads((model.ROOT/'conformance/rc7-carriers-v1/cases/fragment-file.json').read_text())
        pair=deepcopy(core);pair.update({k:fixtures.fixture()['fragment'][k] for k in ['command_root','path_prepend']})
        self.assertTrue(candidate.is_valid(core),'no B-a members')
        self.assertTrue(candidate.is_valid(pair),'paired B-a members')
        for key in ['command_root','path_prepend','codex_settings']:
            bad=deepcopy(pair);bad.pop(key)
            self.assertFalse(candidate.is_valid(bad),key)
        bad=deepcopy(pair);bad['credential_store']['config_overrides']={'cli_auth_credentials_store':'file'}
        self.assertFalse(candidate.is_valid(bad),'legacy Codex ownership')
        self.assertFalse(candidate.is_valid(dict(pair,extra=True)),'unknown member')
        checks=model.validators()
        # The sole normative carrier still rejects the proposed extension.
        from jsonschema import Draft202012Validator
        wire=Draft202012Validator(json.loads((model.ROOT/'schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json').read_text()),registry=checks['native-admission-proposal.schema.json']._registry)
        self.assertFalse(wire.is_valid(pair),'unaccepted production extension')

    def test_final_store_path_bounds(self):
        # Every proposed final path fits at the existing receipt bound; the
        # adjacent over-budget receipt refuses. This excludes journal scratch paths.
        for platform,budget in [('linux-amd64',101),('darwin-arm64',100),('windows-amd64',99)]:
            profile='p'*64; home=('/' if not platform.startswith('windows') else 'C:/')+'m'*(budget-64-(1 if not platform.startswith('windows') else 3))
            paths=proposal.locations(home,profile,'a'*64,platform,'b'*64,'c'*64)
            windows=platform.startswith('windows')
            self.assertTrue(all(model.bounded_path(p,windows) for p in paths.values()),platform)
            self.assertEqual(len(paths['receipt'].encode()),240,platform)
            over=proposal.locations(home+'x',profile,'a'*64,platform,'b'*64,'c'*64)
            self.assertFalse(model.bounded_path(over['receipt'],windows),platform+' receipt 241')

    def test_request_decoder_and_replay_refusal(self):
        # One closed request passes; duplicate keys, trailing records and unknown
        # members refuse before replay and do not modify saved pin/request state.
        raw=json.dumps(self.case['acquire']);saved=deepcopy(self.case['replay'])
        self.assertEqual(proposal.decode_acquire(raw),self.case['acquire'])
        for bad in [raw+' {}','{"record":"bad","record":"bad"}']:
            with self.assertRaisesRegex(model.Refusal,'^candidate-request-json$'):proposal.decode_acquire(bad)
        with self.assertRaisesRegex(model.Refusal,'^candidate-acquire-schema$'):
            proposal.decode_acquire(json.dumps(dict(self.case['acquire'],unknown=True)))
        self.assertEqual(self.case['replay'],saved)

    def test_schema_pair_path_and_replay_plants(self):
        # Specific valid-shape negatives detect weakened schema, pairing, path
        # bound and replay guards; each mutant still admits the valid control.
        from jsonschema import Draft202012Validator
        schema=deepcopy(model.validators()['native-admission-proposal.schema.json'].schema)
        for name,path,value in [
            ('legacy-entry-point',['entry_point','legacy_excluded'],False),
            ('launcher-capability',['launcher','capability'],'fragment-v4')]:
            bad=deepcopy(self.case);bad['policy'][path[0]][path[1]]=value
            self.assertFalse(model.validators()['native-admission-proposal.schema.json'].is_valid(bad),name)
            weakened=deepcopy(schema)
            if name=='legacy-entry-point':weakened['$defs']['policy']['properties']['entry_point']['properties']['legacy_excluded']={}
            else:weakened['$defs']['policy']['properties']['launcher']=deepcopy(weakened['$defs']['policy']['properties']['launcher']);weakened['$defs']['policy']['properties']['launcher']['properties']['capability']={}
            mutant=Draft202012Validator(weakened,registry=model.validators()['native-admission-proposal.schema.json']._registry)
            self.assertTrue(mutant.is_valid(self.case),name+' control')
            self.assertTrue(mutant.is_valid(bad),name+' plant')
            print('plant detected by named vector:',name)
        candidate=proposal.joint_candidate();base=fixtures.fixture()['fragment']
        bare=deepcopy(base);bare.pop('command_root')
        self.assertTrue(candidate.is_valid(base),'joint control')
        self.assertFalse(candidate.is_valid(bare),'bare-prepend')
        weakened=deepcopy(candidate.schema);weakened.pop('dependentRequired')
        mutant=candidate.evolve(schema=weakened)
        self.assertTrue(mutant.is_valid(base),'joint mutant control')
        self.assertTrue(mutant.is_valid(bare),'bare-prepend plant')
        print('plant detected by named vector: bare-prepend')
        source=Path(model.__file__).read_text();ns={'__file__':model.__file__,'__name__':'bound_plant'}
        exec(compile(source.replace('len(path.encode()) <= 240','len(path.encode()) <= 241'),model.__file__,'exec'),ns)
        receipt=proposal.locations('/'+'m'*97,'work','a'*64,'linux-amd64','b'*64,'c'*64)['receipt']
        self.assertEqual(len(receipt),241,'receipt-241 shape')
        self.assertTrue(model.bounded_path(receipt[:-1]),'receipt-240 control')
        self.assertFalse(model.bounded_path(receipt),'receipt-241')
        self.assertTrue(ns['bounded_path'](receipt),'receipt-241 plant')
        print('plant detected by named vector: receipt-241')
        source=Path(proposal.__file__).read_text();ns={'__file__':proposal.__file__,'__name__':'replay_plant'}
        exec(compile(source.replace("saved['request'] == request",'True'),proposal.__file__,'exec'),ns)
        request=deepcopy(self.case['acquire']);request['binding']['generation']='f'*64
        self.assertEqual(ns['replay_acquire'](self.case['replay'],self.case['acquire']),self.case['replay']['pin'])
        with self.assertRaisesRegex(model.Refusal,'^session-request-conflict$'):proposal.replay_acquire(self.case['replay'],request)
        self.assertEqual(ns['replay_acquire'](self.case['replay'],request),self.case['replay']['pin'],'changed-generation replay plant')
        print('plant detected by named vector: changed-generation replay')

    def test_native_identity_configuration_only(self):
        # Explicit pair supplies only configuration; inherited conflicts and a
        # half pair refuse unchanged. No flags invents neither identity nor ID.
        env={'PATH':'/tools:/usr/bin'};before=deepcopy(env)
        expected=dict(env,A2A_AGENT='agent-one',A2A_CONFIG_DIR='/identities/one')
        self.assertEqual(proposal.identity_environment(None,None,env),env)
        self.assertEqual(proposal.identity_environment('agent-one','/identities/one',env),expected)
        self.assertEqual(proposal.identity_environment('agent-one','/identities/one',expected),expected)
        for identity,directory,inherited,reason in [
            ('agent-one',None,env,'native-identity-pair'),
            (None,'/identities/one',env,'native-identity-pair'),
            ('agent-one','relative',env,'native-identity-directory'),
            ('agent-one','/identities/one',dict(env,A2A_AGENT='agent-two'),'native-identity-conflict'),
            ('agent-one','/identities/one',dict(env,A2A_CONFIG_DIR='/identities/two'),'native-identity-conflict')]:
            old=deepcopy(inherited)
            with self.subTest(reason=reason),self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):
                proposal.identity_environment(identity,directory,inherited)
            self.assertEqual(inherited,old,reason)
        self.assertEqual(env,before)
        source=Path(proposal.__file__).read_text();ns={'__file__':proposal.__file__,'__name__':'identity_plant'}
        exec(compile(source.replace("inherited.get(key, value) == value",'True'),proposal.__file__,'exec'),ns)
        self.assertEqual(ns['identity_environment']('agent-one','/identities/one',env),expected,'identity control')
        for key,value in [('A2A_AGENT','agent-two'),('A2A_CONFIG_DIR','/identities/two')]:
            conflict=dict(env,**{key:value})
            self.assertEqual(ns['identity_environment']('agent-one','/identities/one',conflict),expected,key+' conflict plant')
            print('plant detected by named vector: native-identity-conflict '+key)

    def test_a9_independent_pin_authorities(self):
        # Each single pin-field substitution is refused against fresh authority;
        # a genuine revision advance admits, with inputs unchanged on refusal.
        data=fixtures.output()
        for section,check,prefix in [('launchers',model.launcher_check,'launcher-session-'),('sessions',model.session_check,'session-')]:
            for case in data[section]:
                if case['id'].startswith(prefix) or case['id'].endswith('next-revision') or case['id'] in ['session-active','launcher-valid','launcher-authority-unknown']:
                    with self.subTest(row=case['id']):
                        before=deepcopy(case['state'])
                        self.assertEqual(model.decision(check,case['state']),(case['expected'],case['reason']),case['id'])
                        self.assertEqual(case['state'],before,case['id'])

    def test_a10_restore_edges_and_post_refusal_state(self):
        # Plain/live/unknown are different inputs. Unknown needs quiescence or
        # fenced audited break; repair never drops/retargets old edge evidence.
        rows={c['id']:c for c in fixtures.output()['transactions']}
        names=['repair-explicit','repair-pinned-restore','repair-stale-session','repair-stale-reconciled','repair-stale-broken','repair-stale-unfenced','repair-stale-unaudited','repair-stale-revision','repair-stale-descendant','repair-retargeted','repair-live-dropped']
        self.assertEqual([rows[n]['state']['retained_edge']['kind'] for n in names[:3]],['none','live-session','unknown-session'])
        for name in names:
            with self.subTest(row=name):
                case=rows[name];before=deepcopy(case['state']);actual=model.transaction(case['state'])
                self.assertEqual(actual,case['expected'],name)
                self.assertEqual(actual['retained_edge'],before['retained_edge'],name)
                if case['expected']['outcome']=='refuse-unchanged':self.assertEqual(actual['live'],before['before'],name)
                self.assertEqual(case['state'],before,name)

    def test_named_guard_plants(self):
        # Removing each candidate/A9/A10 guard changes its named witness, while
        # the nearby valid control still passes; crashes do not count as detection.
        import ast
        modules=[(proposal,proposal.check_candidate), (model,model.pin_authority)]
        for module,function in modules:
            source=Path(module.__file__).read_text();tree=ast.parse(source)
            node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==function.__name__)
            guards=[n for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='require']
            if module is proposal:
                mutations=[('candidate-selected-lock',lambda c:c['policy']['profiles'][0].update(lock_sha256='f'*64)),('candidate-generation-location',lambda c:c['generation'].update(inventory='/outside/inventory.json'))]
                for reason,change in mutations:
                    guard=next(n for n in guards if isinstance(n.args[1],ast.Constant) and n.args[1].value==reason)
                    old=ast.get_source_segment(source,guard.args[0]);mutated=source.replace(old,'True',1)
                    ns={'__file__':module.__file__,'__name__':'guard_plant'};exec(compile(mutated,module.__file__,'exec'),ns)
                    bad=deepcopy(self.case);change(bad)
                    ns['check_candidate'](self.case,self.trusted)
                    with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.check_candidate(bad,self.trusted)
                    ns['check_candidate'](bad,self.trusted)
                    print('plant detected by named vector:',reason)
            else:
                # Replacing the shared field comparison recreates all six A9
                # defects at once; each named well-shaped negative changes verdict.
                ns={'__file__':module.__file__,'__name__':'guard_plant'}
                exec(compile(source.replace("pin[field] == authority[field]",'True'),module.__file__,'exec'),ns)
                for case in fixtures.output()['launchers']:
                    if case['id'] in {'launcher-valid','launcher-next-revision'}:
                        self.assertEqual(ns['decision'](ns['launcher_check'],case['state']),('accept','verified'))
                    if case['id'] in {'launcher-session-'+n for n in ['revision','supervisor','boot','domain','start','request']} | {'launcher-authority-unknown'}:
                        self.assertEqual(model.decision(model.launcher_check,case['state']),(case['expected'],case['reason']))
                        self.assertEqual(ns['decision'](ns['launcher_check'],case['state']),('accept','verified'),case['id'])
                        print('plant detected by named vector:',case['id'])
        source=Path(model.__file__).read_text()
        for expression,witness in [("edge['kind'] == 'unknown-session'","repair-stale-session"),("state['staged_edge'] != edge","repair-retargeted"), ("state['audit_durable']",'repair-stale-unaudited'), ("state['if_revision'] == edge['revision']",'repair-stale-revision'), ("state['descendants_quiescent']",'repair-stale-descendant')]:
            ns={'__file__':model.__file__,'__name__':'guard_plant'};replacement='False' if expression in ["edge['kind'] == 'unknown-session'","state['staged_edge'] != edge"] else 'True'
            exec(compile(source.replace(expression,replacement),model.__file__,'exec'),ns)
            rows={c['id']:c for c in fixtures.output()['transactions']}
            valid=rows['repair-pinned-restore'];bad=rows[witness]
            self.assertEqual(ns['transaction'](valid['state']),valid['expected'])
            self.assertEqual(model.transaction(bad['state']),bad['expected'])
            self.assertNotEqual(ns['transaction'](bad['state']),bad['expected'],witness)
            print('plant detected by named vector:',witness)


if __name__=='__main__':unittest.main()
