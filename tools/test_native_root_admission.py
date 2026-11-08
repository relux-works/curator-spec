"""Named spec/model controls and guard plants; no runtime qualification."""
from copy import deepcopy
import ast
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator
from referencing import Resource

import native_root_admission as proposal
import profile_command_roots as model
import generate_profile_command_roots as fixtures


class NativeRootAdmission(unittest.TestCase):
    def setUp(self):
        self.base=json.loads((model.CORPUS/'native-admission-proposal.json').read_text(encoding='utf-8'))
        self.case=deepcopy(self.base);self.case['variant']='pins'
        self.case['session']=json.loads((model.CORPUS/'native-pins-alternative.json').read_text(encoding='utf-8'))
        p=self.base['policy']
        self.observed=dict(home='/home/agent/.curator',uid=1000,policy_revision=1,
                           selected=deepcopy(self.base['selected']),
                           request=deepcopy(self.case['session']['request']),
                           **{k:deepcopy(p[k]) for k in ['manager','launcher']})

    def mutant(self, module, function, reason=None, expression=None, replacement='True'):
        source=Path(module.__file__).read_text(encoding='utf-8')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==function)
        if expression is None:
            guard=next(n for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                       and n.func.id=='require' and isinstance(n.args[1],ast.Constant) and n.args[1].value==reason)
            expression=ast.get_source_segment(source,guard.args[0])
        start=sum(len(line) for line in source.splitlines(keepends=True)[:node.body[0].lineno-1])
        index=source.index(expression,start)
        mutated=source[:index]+replacement+source[index+len(expression):]
        ns={'__file__':module.__file__,'__name__':'guard_plant'}
        exec(compile(mutated,module.__file__,'exec'),ns)
        return ns

    def test_candidate_guards_and_plants(self):
        # Each coherent invalid candidate refuses by its intended reason without
        # input writes; removing that guard admits it and still admits the control.
        def home(c,o):c['policy']['manager_home']=o['home']='/'+'m'*150
        def linux(c,o):
            for obj in [c['selected'],c['session']['request'],c['session']['pin']]:obj['binding']['platform']='darwin-arm64'
            o['selected']=deepcopy(c['selected']);o['request']=deepcopy(c['session']['request'])
        def request_binding(c,o):
            for obj in [c['session']['request'],c['session']['pin']]:obj['binding']['generation']='f'*64
            o['request']=deepcopy(c['session']['request'])
        def request_authority(c,o):
            for obj in [c['session']['request'],c['session']['pin']]:obj['supervisor_instance']='f'*64
        changes=[
            ('candidate-policy-authority',lambda c,o:c['policy'].update(uid=2000)),
            ('candidate-manager',lambda c,o:c['policy']['manager'].update(sha256='f'*64)),
            ('candidate-launcher',lambda c,o:c['policy']['launcher'].update(sha256='f'*64)),
            ('candidate-selected-lock',lambda c,o:c['policy']['profiles'][0].update(lock_sha256='f'*64)),
            ('candidate-profile-duplicate',lambda c,o:c['policy']['profiles'].append(dict(c['policy']['profiles'][0],lock_sha256='f'*64))),
            ('candidate-selection',lambda c,o:c['selected'].update(revision=2)),
            ('candidate-native-linux',linux),('candidate-path-limit',home),
            ('candidate-request-binding',request_binding),
            ('candidate-issued-phase',lambda c,o:c['session']['pin'].update(phase='prepared')),
            ('candidate-issued-phase',lambda c,o:c['session']['pin'].update(revision=2)),
            ('candidate-request-authority',request_authority),
            ('candidate-session-key',lambda c,o:c['session']['pin'].update(lease_id='f'*64)),
        ]
        for reason,change in changes:
            with self.subTest(reason=reason):
                bad=deepcopy(self.case);observed=deepcopy(self.observed);change(bad,observed);before=deepcopy((bad,observed))
                proposal.check_candidate(self.case,self.observed)
                with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.check_candidate(bad,observed)
                self.assertEqual((bad,observed),before)
                mutant=self.mutant(proposal,'check_candidate',reason,expression="absolute(policy[name]['path']) and policy[name] == observed[name]" if reason in {'candidate-manager','candidate-launcher'} else None)
                mutant['check_candidate'](self.case,self.observed)
                mutant['check_candidate'](bad,observed)
                print('plant detected by named vector:',reason)
        # The shared issued-field guard is exercised separately for each field.
        mutant=self.mutant(proposal,'check_candidate',expression='req[key] == pin[key]')
        for key in ['request_id','profile','binding','supervisor_instance','boot_id','process_domain','process_started_at']:
            bad=deepcopy(self.case);pin=bad['session']['pin']
            if key=='binding':pin[key]['generation']='f'*64
            elif key=='profile':pin[key]='Other.1'
            else:pin[key]='f'*64
            reason='candidate-issued-'+key
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.check_candidate(bad,self.observed)
            mutant['check_candidate'](self.case,self.observed)
            mutant['check_candidate'](bad,self.observed)
            print('plant detected by named vector:',reason)

    def test_authority_clause_vectors_and_plants(self):
        # Each independent home/revision/profile clause has a coherent failing
        # vector; its removal admits that vector and the unchanged valid control.
        for label,reason,expression,change in [
            ('candidate-home','candidate-policy-authority',"policy['manager_home'] == observed['home']",lambda c:c['policy'].update(manager_home='/other-home')),
            ('candidate-policy-revision','candidate-policy-authority',"policy['revision'] == observed['policy_revision']",lambda c:c['policy'].update(revision=2)),
            ('candidate-selected-profile','candidate-selected-lock',"p['profile'] == selected['profile']",lambda c:c['policy']['profiles'][0].update(profile='Other.1'))]:
            bad=deepcopy(self.base);change(bad);before=deepcopy(bad)
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.check_candidate(bad,self.observed)
            mutant=self.mutant(proposal,'check_candidate',expression=expression)
            mutant['check_candidate'](self.base,self.observed);mutant['check_candidate'](bad,self.observed)
            self.assertEqual(bad,before)
            print('plant detected by named vector:',label)

    def test_home_route_vectors_and_plants(self):
        # H with absent policy and a B-a pair without H refuse before use. A
        # conflicting inherited config refuses; valid and legacy controls pass.
        home=self.observed['home'];policy=self.base['policy'];config=home+'/config.json'
        self.assertIsNone(proposal.home_route(None,False,None))
        for inherited in [None,'',config]:self.assertEqual(proposal.home_route(home,True,policy,inherited),config)
        for reason,args in [('native-home-required',(None,True,policy)),
                            ('native-policy-required',(home,True,None)),
                            ('native-home-conflict',(home,True,policy,'/other/config.json'))]:
            before=deepcopy(args)
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.home_route(*args)
            mutant=self.mutant(proposal,'home_route',reason)
            self.assertEqual(mutant['home_route'](home,True,policy),config)
            mutant['home_route'](*args);self.assertEqual(args,before)
            print('plant detected by named vector:',reason)
        bad=deepcopy(self.base);bad.pop('policy');before=deepcopy(bad)
        with self.assertRaisesRegex(model.Refusal,'^candidate-schema$'):proposal.check_candidate(bad,self.observed)
        self.assertEqual(bad,before)

    def test_managed_package_root_vector_and_plant(self):
        # An installed package supplied as an abstract mapping precedes PATH in
        # Codex resolution. Refuse an unsanitized H-route environment before any
        # stage; deleting the guard selects that package despite admitted PATH.
        # No actual package layout, SAM, filesystem or provider is exercised.
        home=self.base['policy']['manager_home']
        package=home+'/environments/Work.1/commands/old/package'
        binary=package+'/vendor/x86_64-unknown-linux-musl/bin/codex'
        admitted=['/usr/bin','/bin']
        good={stage:dict(PATH=':'.join(admitted)) for stage in ('resolve','probe','plan')}
        executables={binary,'/usr/bin/codex'};packages={package:binary}
        expected={stage:'/usr/bin/codex' for stage in good}
        self.assertEqual(proposal.provider_path_observations('codex',admitted,good,executables,packages),expected)
        mutant=self.mutant(proposal,'provider_path_observations','native-provider-managed-package-root')
        self.assertEqual(mutant['provider_path_observations']('codex',admitted,good,executables,packages),expected)
        for stage, package in [(stage, package) for stage in good] + [('plan','/outside/managed-codex')]:
            if package == '/outside/managed-codex':
                binary=package+'/vendor/x86_64-unknown-linux-musl/bin/codex'
                executables.add(binary);packages[package]=binary
                self.assertEqual(proposal.provider_path_observations('codex',admitted,good,executables,packages),expected)
                self.assertEqual(mutant['provider_path_observations']('codex',admitted,good,executables,packages),expected)
            bad=deepcopy(good);bad[stage]['CODEX_MANAGED_PACKAGE_ROOT']=package
            before=deepcopy((admitted,bad,executables,packages))
            with self.assertRaisesRegex(model.Refusal,'^native-provider-managed-package-root$'):
                proposal.provider_path_observations('codex',admitted,bad,executables,packages)
            self.assertEqual(mutant['provider_path_observations']('codex',admitted,bad,executables,packages)[stage],binary)
            self.assertEqual((admitted,bad,executables,packages),before)
        print('plant detected by named vector: provider-managed-package-root (native-provider-managed-package-root)')
        print('plant detected by named vector: provider-managed-package-root-outside-home (native-provider-managed-package-root)')

    def test_provider_named_decoy_path_and_plant(self):
        # Compose spelling exclusion with the ordered recheck and supplied
        # resolve/probe/plan PATH observations. A decoy exists only as a name;
        # this proves the model guard, not real resolution, execution or SAM.
        import test_profile_command_path as path_model
        home=self.base['policy']['manager_home']
        data=path_model.load(path_model.CORPUS/'baseline.json');data['policy']='managed'
        excluded=home+'/environments/Work.1/commands/substituted/bin'
        data['base_path']=[excluded]+data['base_path']
        data['path_facts'][excluded]=dict(identity='substituted',readable=True,kind='directory',mode=511)
        admitted,issues,exclusions=path_model.admit_path(data,[],manager_home=home)
        self.assertEqual(issues,[]);self.assertEqual(exclusions,[excluded])
        record=dict(record='candidate/native-base-path/1',manager_home=home,uid=self.base['policy']['uid'],
                    policy_revision=self.base['policy']['revision'],platform='linux-amd64',retained=['/usr/bin','/bin'])
        self.assertEqual(proposal.base_path_recheck(record,self.base['policy'],'linux-amd64',admitted),record['retained'])
        good={stage:dict(PATH=':'.join(admitted)) for stage in ('resolve','probe','plan')}
        executables={excluded+'/codex','/usr/bin/codex'}
        expected={stage:'/usr/bin/codex' for stage in good}
        self.assertEqual(proposal.provider_path_observations('codex',admitted,good,executables),expected)
        mutant=self.mutant(proposal,'provider_path_observations','native-provider-admitted-path')
        self.assertEqual(mutant['provider_path_observations']('codex',admitted,good,executables),expected)
        for stage in good:
            bad=deepcopy(good);bad[stage]['PATH']=':'.join(data['base_path'])
            before=deepcopy((admitted,bad,executables))
            with self.assertRaisesRegex(model.Refusal,'^native-provider-admitted-path$'):
                proposal.provider_path_observations('codex',admitted,bad,executables)
            self.assertEqual(mutant['provider_path_observations']('codex',admitted,bad,executables)[stage],
                             excluded+'/codex')
            self.assertEqual((admitted,bad,executables),before)
        print('plant detected by named vector: provider-named-decoy-admitted-path (native-provider-admitted-path)')

    def test_home_delivery_vectors_and_plants(self):
        # On H launches, supplied planning/tool observations must name H even
        # without identity. A missing/different locator fails by intended reason;
        # this does not execute SAM, inherit=core or a provider tool shell.
        config = self.base['policy']['manager_home']+'/config.json'
        for identity in [False, True]:
            good = dict(CURATOR_CONFIG=config)
            if identity:
                good.update(A2A_AGENT='lane', A2A_CONFIG_DIR='/fixture/a2a')
            proposal.home_delivery(config, good, good)
            for field, reason in [('plan', 'native-home-plan-delivery'),
                                  ('tool', 'native-home-tool-delivery')]:
                for value in [None, '/default/config.json']:
                    plan, tool = deepcopy(good), deepcopy(good)
                    target = plan if field == 'plan' else tool
                    if value is None: target.pop('CURATOR_CONFIG')
                    else: target['CURATOR_CONFIG'] = value
                    before = deepcopy((plan, tool))
                    with self.assertRaisesRegex(model.Refusal, '^'+reason+'$'):
                        proposal.home_delivery(config, plan, tool)
                    self.assertEqual((plan, tool), before)
                    mutant = self.mutant(proposal, 'home_delivery', reason)
                    mutant['home_delivery'](config, good, good)
                    mutant['home_delivery'](config, plan, tool)
                    self.assertEqual((plan, tool), before)
                    print('plant detected by named vector:', reason+'-'+
                          ('identity' if identity else 'no-identity')+'-'+
                          ('absent' if value is None else 'different'))

    def test_home_namespace_spelling_vectors_and_plant(self):
        # Missing or unsafe entries spelled inside H's namespace are excluded
        # without facts. Lookalike/foreign paths still refuse under unattended
        # policy; dot/control paths drop before exclusion. No native FS queried.
        import test_profile_command_path as path_model
        home = self.base['policy']['manager_home']
        data = path_model.load(path_model.CORPUS/'baseline.json')
        data['policy'] = 'managed'
        control = deepcopy(data)
        root = home+'/environments/Work.1/commands/old/linux-amd64/bin'
        prefix = home+'/environments/'
        for entry in [root, root+'/nested', prefix+'Work.1/commands']:
            for fact in [None, dict(identity='substituted', readable=True, kind='directory', mode=511)]:
                case = deepcopy(data);case['base_path'] = [entry]+data['base_path']
                if fact is not None: case['path_facts'][entry] = fact
                before = deepcopy(case)
                kept, issues, excluded = path_model.admit_path(case, [], manager_home=home)
                self.assertEqual((kept, issues, excluded), (data['base_path'], [], [entry]))
                self.assertEqual(case, before)
        for entry in [home+'-other/environments/Work.1/commands/old/bin',
                      prefix+'Work.1/commands-other/bin', prefix+'Work.1./commands/bin',
                      '/outside/missing', '/outside/unsafe']:
            case = deepcopy(data);case['base_path'] = [entry]+data['base_path']
            if entry.endswith('/unsafe'):
                case['path_facts'][entry] = dict(identity='unsafe',readable=True,kind='directory',mode=511)
            _, issues, excluded = path_model.admit_path(case, [], manager_home=home)
            self.assertEqual(excluded, [])
            self.assertEqual(issues, [dict(entry=entry, predicate=('world-writable' if entry.endswith('/unsafe')
                                                                  else 'unreadable'), action='refuse')])
        for entry, predicate in [(prefix+'Work.1/commands/../bin', 'non-canonical'),
                                 (root+'\n', 'control-characters')]:
            case=deepcopy(data);case['base_path']=[entry]+data['base_path']
            _, issues, excluded=path_model.admit_path(case, [], manager_home=home)
            self.assertEqual(excluded, [])
            self.assertEqual(issues, [dict(entry=entry,predicate=predicate,action='drop')])
        case=deepcopy(data);case['base_path']=[root]+data['base_path']
        expression = "manager_home is not None and entry.startswith(manager_home+'/environments/')\n              and re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9_-])?/commands(?:/.*)?',\n                               entry[len(manager_home+'/environments/'):])"
        mutant=self.mutant(path_model,'admit_path',expression=expression,replacement='False')
        self.assertEqual(mutant['admit_path'](control,[],manager_home=home),
                         path_model.admit_path(control,[],manager_home=home))
        kept, issues, excluded=mutant['admit_path'](case,[],manager_home=home)
        self.assertEqual(excluded, [])
        self.assertEqual(issues,[dict(entry=root,predicate='unreadable',action='refuse')])
        self.assertEqual(kept,data['base_path'])
        print('plant detected by named vector: base-path-pruned-home-root-exclusion (unreadable)')

    def test_candidate_home_route_wiring(self):
        # A real candidate path drives the config conflict; deleting the helper
        # call admits that exact conflict while the valid control still passes.
        bad=deepcopy(self.observed);bad['config']='/other/config.json'
        before=deepcopy(bad)
        with self.assertRaisesRegex(model.Refusal,'^native-home-conflict$'):
            proposal.check_candidate(self.base,bad)
        mutant=self.mutant(proposal,'check_candidate',
            expression="home_route(observed['home'], True, case['policy'], observed.get('config'))",replacement='None')
        mutant['check_candidate'](self.base,self.observed)
        mutant['check_candidate'](self.base,bad)
        self.assertEqual(bad,before)
        print('plant detected by named vector: candidate-home-route-wiring')

    def test_route_refusals_and_spawn_recheck(self):
        # Route refusals precede the conceptual plan boundary; these pure models
        # do not run a launcher. Hosted legacy identity and ordinary gateway pass.
        for args in [(False,False,True,True),(False,True,False,False),(True,False,False,False)]:
            self.assertEqual(proposal.native_route(*args),'admitted-route')
        for label,reason,args in [
            ('hosted-native-pair','fragment_version_unsupported',(True,False,True,False)),
            ('gateway-native-pair','native_root_gateway_unsupported',(False,True,True,False)),
            ('gateway-native-identity','native_root_gateway_unsupported',(False,True,False,True))]:
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.native_route(*args)
            mutant=self.mutant(proposal,'native_route',reason)
            self.assertEqual(mutant['native_route'](False,False,True,True),'admitted-route')
            self.assertEqual(mutant['native_route'](*args),'admitted-route')
            print('plant detected by named vector:',label)
        # Both independent revision changes refuse, unchanged observations pass.
        good=dict(policy_revision=1,selection_revision=1)
        proposal.spawn_recheck(1,1,good)
        for key in good:
            bad=dict(good);bad[key]=2;reason='native-spawn-'+key.replace('_','-')
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.spawn_recheck(1,1,bad)
            mutant=self.mutant(proposal,'spawn_recheck',reason)
            mutant['spawn_recheck'](1,1,good);mutant['spawn_recheck'](1,1,bad)
            self.assertEqual(bad[key],2)
            print('plant detected by named vector:',reason)

    def test_base_path_evidence_and_ordered_recheck(self):
        # Shape/binding/ordered classified-list differences refuse with no writes.
        # Classification/exclusion observations are supplied, not native proof.
        good=dict(record='candidate/native-base-path/1',manager_home=self.observed['home'],
                  uid=1000,policy_revision=1,platform='linux-amd64',retained=['/usr/bin','/bin'])
        def check(record,retained):
            return proposal.base_path_recheck(record,self.base['policy'],'linux-amd64',retained)
        self.assertEqual(check(good,good['retained']),good['retained'])
        for label,reason,record,retained in [
            ('base-path-closed-shape','native-base-path-schema',dict(good,extra=True),good['retained']),
            ('base-path-home','native-base-path-binding',dict(good,manager_home='/other'),good['retained']),
            ('base-path-uid','native-base-path-binding',dict(good,uid=1001),good['retained']),
            ('base-path-revision','native-base-path-binding',dict(good,policy_revision=2),good['retained']),
            ('base-path-platform','native-base-path-binding',dict(good,platform='linux-arm64'),good['retained']),
            ('base-path-noncanonical','native-base-path-schema',dict(good,retained=['/usr/../bin']),['/usr/../bin']),
            ('base-path-control','native-base-path-schema',dict(good,retained=['/usr/\x85bin']),['/usr/\x85bin']),
            ('base-path-relative','native-base-path-schema',dict(good,retained=['relative']),['relative']),
            ('base-path-duplicate','native-base-path-schema',dict(good,retained=['/bin','/bin']),['/bin','/bin']),
            ('base-path-reordered','native-base-path-difference',good,['/bin','/usr/bin']),
            ('base-path-added','native-base-path-difference',good,good['retained']+['/new']),
            ('base-path-removed','native-base-path-difference',good,['/usr/bin'])]:
            before=deepcopy((record,retained))
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):check(record,retained)
            mutant=self.mutant(proposal,'base_path_recheck',reason)
            mutant['base_path_recheck'](good,self.base['policy'],'linux-amd64',good['retained'])
            mutant['base_path_recheck'](record,self.base['policy'],'linux-amd64',retained)
            self.assertEqual((record,retained),before)
            print('plant detected by named vector:',label)
        # Existing section-3 classifier supplies the inherited-root positive and
        # its own namespace-exclusion plant, rather than duplicating that logic.
        import test_profile_command_path as path_model
        data=path_model.load(path_model.CORPUS/'baseline.json');data['policy']='managed'
        ordinary=deepcopy(data);ordinary['base_path']=good['retained']
        data['path_facts']['/alias/old-root']=deepcopy(data['path_facts']['/foreign/profile/bin'])
        data['base_path']=['/foreign/profile/bin','/fixture/domain/global/bin','/alias/old-root']+good['retained']
        retained,issues,excluded=path_model.admit_path(data,[])
        self.assertEqual(issues,[]);self.assertEqual(excluded,data['base_path'][:3])
        self.assertEqual(check(good,retained),good['retained'])
        mutant=self.mutant(path_model,'admit_path',expression="fact['identity'] in root_ids",replacement='False')
        self.assertEqual(check(good,mutant['admit_path'](ordinary,[])[0]),good['retained'])
        with self.assertRaisesRegex(model.Refusal,'^native-base-path-difference$'):
            check(good,mutant['admit_path'](data,[])[0])
        print('plant detected by named vector: base-path-inherited-root-exclusion')

    def test_unpinned_launch_allocation_and_plants(self):
        # Closed no-lease provenance binds prior/full selection, observations and
        # final PATH; shape/field substitutions refuse without mutating records.
        source=fixtures.launcher(fixtures.fixture())['record']
        good=deepcopy(source);good.pop('lease_id');good.update(record='candidate/native-root-launch/1',
            policy_revision=1,selection_revision=1,base_path_sha256='a'*64)
        profile=self.base['selected']['profile'];binding=good['command_root'];effective=good['effective_path']
        good['prior_state']['binding']=dict(profile=profile,lock_sha256='sha256:'+binding['lock_sha256'],
            plan_sha256='sha256:'+binding['plan_sha256'],generation=binding['generation'])
        good['prior_state']['path']=deepcopy(effective);good['prior_state']['path_value']=good['path_value']
        args=(profile,binding,1,1,'a'*64,effective)
        self.assertEqual(proposal.unpinned_launch(good,*args),good)
        for label,reason,change in [
            ('unpinned-forbids-lease','native-unpinned-schema',lambda c:c.update(lease_id='b'*64)),
            ('unpinned-binding','native-unpinned-binding',lambda c:c['command_root'].update(generation='f'*64)),
            ('unpinned-prior','native-unpinned-prior',lambda c:c['prior_state']['binding'].update(profile='other')),
            ('unpinned-policy-revision','native-unpinned-observation',lambda c:c.update(policy_revision=2)),
            ('unpinned-selection-revision','native-unpinned-observation',lambda c:c.update(selection_revision=2)),
            ('unpinned-base-evidence','native-unpinned-observation',lambda c:c.update(base_path_sha256='b'*64)),
            ('unpinned-path-order','native-unpinned-path',lambda c:c['effective_path'].reverse()),
            ('unpinned-path-value','native-unpinned-path',lambda c:c.update(path_value='/other')),
            ('unpinned-prior-path','native-unpinned-path',lambda c:c['prior_state'].update(path=['/other']))]:
            bad=deepcopy(good);change(bad);before=deepcopy(bad)
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.unpinned_launch(bad,*args)
            mutant=self.mutant(proposal,'unpinned_launch',reason)
            self.assertEqual(mutant['unpinned_launch'](good,*args),good)
            self.assertEqual(mutant['unpinned_launch'](bad,*args),bad)
            self.assertEqual(bad,before)
            print('plant detected by named vector:',label)
        # A coherently supplied foreign-platform binding still fails the new
        # Linux-only record allocation, rather than an unrelated binding check.
        bad=deepcopy(good);bad['command_root']['platform']='darwin-arm64'
        foreign_args=(profile,bad['command_root'],1,1,'a'*64,effective)
        with self.assertRaisesRegex(model.Refusal,'^native-unpinned-schema$'):
            proposal.unpinned_launch(bad,*foreign_args)
        mutant=self.mutant(proposal,'unpinned_launch','native-unpinned-schema')
        self.assertEqual(mutant['unpinned_launch'](good,*args),good)
        self.assertEqual(mutant['unpinned_launch'](bad,*foreign_args),bad)
        print('plant detected by named vector: unpinned-linux-only')
        # Full-pins record still requires its lease and rejects this new token.
        self.assertTrue(model.validators()['launcher-state.schema.json'].is_valid(source))
        self.assertFalse(model.validators()['launcher-state.schema.json'].is_valid(good))

    def test_recommended_variant_and_grammar(self):
        # Operator-prune admission has no session; pin data is rejected there.
        # Work.1 is valid across policy, selection and optional session records.
        paths=proposal.check_candidate(self.base,self.observed)
        self.assertNotIn('session',paths)
        self.assertNotIn('generation',paths)
        self.assertNotIn('replay',paths)
        for variant in ['operator-prune','pins']:
            case=deepcopy(self.case if variant=='pins' else self.base);obs=deepcopy(self.observed)
            case['policy']['profiles'][0]['profile']=case['selected']['profile']='Work.1'
            obs['selected']=deepcopy(case['selected'])
            if variant=='pins':
                for obj in [case['session']['request'],case['session']['pin']]:obj['profile']='Work.1'
                obs['request']=deepcopy(case['session']['request'])
            proposal.check_candidate(case,obs)
        # Shape refusal precedes semantic indexing; malformed JSON values never crash.
        invalids=[None,[],0,'invalid',dict(self.base,session=self.case['session']),dict(self.base,variant='pins')]
        for bad in invalids:
            with self.assertRaisesRegex(model.Refusal,'^candidate-schema$'):proposal.check_candidate(bad,self.observed)
        bad=deepcopy(self.base);bad['policy']['manager']['path']='curator'
        with self.assertRaisesRegex(model.Refusal,'^candidate-schema$'):proposal.check_candidate(bad,self.observed)
        # Removing shape validation admits this schema-only unknown member.
        bad=deepcopy(self.base);bad['policy']['writer_cohort']='operator-controlled'
        mutant=self.mutant(proposal,'check_candidate','candidate-schema')
        with self.assertRaisesRegex(model.Refusal,'^candidate-schema$'):proposal.check_candidate(bad,self.observed)
        mutant['check_candidate'](self.base,self.observed);mutant['check_candidate'](bad,self.observed)
        print('plant detected by named vector: candidate-schema')

    def test_candidate_schema_branch_and_token_plants(self):
        # The no-pin/pins branch is explicit; old colliding tokens and malformed
        # profile names refuse. Each relaxed schema still admits valid controls.
        check=model.validators()['native-admission-proposal.schema.json']
        for label,change,weaken in [
            ('operator-prune-with-session',lambda c:c.update(session=self.case['session']),lambda s:s.pop('allOf')),
            ('pins-without-session',lambda c:c.update(variant='pins'),lambda s:s.pop('allOf')),
            ('policy-old-token',lambda c:c['policy'].update(record='candidate/profile-command-admission/1'),lambda s:s['$defs']['policy']['properties'].update(record={})),
            ('candidate-profile-grammar',lambda c:c['selected'].update(profile='Work/1'),lambda s:s['$defs'].update(profile={'type':'string'}))]:
            bad=deepcopy(self.base);change(bad)
            self.assertFalse(check.is_valid(bad),label)
            schema=deepcopy(check.schema);weaken(schema)
            mutant=Draft202012Validator(schema,registry=check._registry.with_resource(schema['$id'],Resource.from_contents(schema)))
            self.assertTrue(mutant.is_valid(self.base),label+' recommended control')
            self.assertTrue(mutant.is_valid(self.case),label+' pins control')
            self.assertTrue(mutant.is_valid(bad),label+' plant')
            print('plant detected by named vector:',label)

    def test_conditional_joint_carrier_and_plants(self):
        # Neither/paired B-a members pass; half pairs and non-Linux B-a refuse.
        # Production schema still rejects the candidate extension.
        candidate=proposal.joint_candidate()
        core=json.loads((model.ROOT/'conformance/rc7-carriers-v1/cases/fragment-file.json').read_text(encoding='utf-8'))
        pair=deepcopy(core);pair.update({k:fixtures.fixture()['fragment'][k] for k in ['command_root','path_prepend']})
        self.assertTrue(candidate.is_valid(core));self.assertTrue(candidate.is_valid(pair))
        for key in ['command_root','path_prepend','codex_settings']:
            bad=deepcopy(pair);bad.pop(key);self.assertFalse(candidate.is_valid(bad),key)
        bad=deepcopy(pair);bad['credential_store']['config_overrides']={'cli_auth_credentials_store':'file'}
        self.assertFalse(candidate.is_valid(bad),'legacy Codex ownership')
        self.assertFalse(candidate.is_valid(dict(pair,extra=True)))
        wire=Draft202012Validator(json.loads((model.ROOT/'schemas/rc7-carriers-v1/launch-env-fragment-v5.schema.json').read_text(encoding='utf-8')),registry=model.validators()['native-admission-proposal.schema.json']._registry)
        self.assertFalse(wire.is_valid(pair))
        bare=deepcopy(pair);bare.pop('command_root');schema=deepcopy(candidate.schema);schema.pop('dependentRequired')
        mutant=candidate.evolve(schema=schema)
        self.assertFalse(candidate.is_valid(bare));self.assertTrue(mutant.is_valid(pair));self.assertTrue(mutant.is_valid(bare))
        print('plant detected by named vector: bare-prepend')
        foreign=deepcopy(pair);foreign['command_root']['platform']='darwin-arm64'
        schema=deepcopy(candidate.schema);schema['properties']['command_root']['properties']['platform']={'enum':['linux-amd64','linux-arm64','darwin-arm64']}
        mutant=candidate.evolve(schema=schema)
        self.assertFalse(candidate.is_valid(foreign),'joint-native-linux')
        self.assertTrue(mutant.is_valid(pair));self.assertTrue(mutant.is_valid(foreign))
        print('plant detected by named vector: joint-native-linux')

    def test_final_store_path_bounds_and_plant(self):
        # Actual final paths fit at the receipt boundary; one extra unit refuses.
        # Journal paths remain unqualified; Darwin/Windows are arithmetic only.
        for platform,budget in [('linux-amd64',101),('darwin-arm64',100),('windows-amd64',99)]:
            windows=platform.startswith('windows');prefix='C:/' if windows else '/'
            profile='p'*64;home=prefix+'m'*(budget-64-len(prefix))
            paths=proposal.locations(home,profile,'a'*64,platform,'b'*64)
            self.assertTrue(all(model.bounded_path(p,windows) for p in paths.values()),platform)
            self.assertEqual(len(paths['receipt'].encode()),240,platform)
            over=proposal.locations(home+'x',profile,'a'*64,platform,'b'*64)
            self.assertFalse(model.bounded_path(over['receipt'],windows))
        ns=self.mutant(model,'bounded_path',expression='len(path.encode()) <= 240',replacement='len(path.encode()) <= 241')
        receipt=proposal.locations('/'+'m'*97,'work','a'*64,'linux-amd64')['receipt']
        self.assertEqual(len(receipt),241)
        self.assertTrue(model.bounded_path(receipt[:-1]));self.assertTrue(ns['bounded_path'](receipt[:-1]))
        self.assertFalse(model.bounded_path(receipt));self.assertTrue(ns['bounded_path'](receipt))
        print('plant detected by named vector: receipt-241')

    def test_decoder_and_one_record_replay(self):
        # Same-process exact request replay returns the saved pin; changed G,
        # duplicate/trailing/unknown JSON refuses without altering the session.
        request=self.case['session']['request'];saved=self.case['session'];before=deepcopy(saved)
        raw=json.dumps(request);self.assertEqual(proposal.decode_acquire(raw),request)
        for bad in [raw+' {}','{"record":"bad","record":"bad"}']:
            with self.assertRaisesRegex(model.Refusal,'^candidate-request-json$'):proposal.decode_acquire(bad)
        with self.assertRaisesRegex(model.Refusal,'^candidate-acquire-schema$'):proposal.decode_acquire(json.dumps(dict(request,unknown=True)))
        self.assertEqual(proposal.replay_acquire(saved,request),saved['pin'])
        bad=deepcopy(request);bad['binding']['generation']='f'*64
        with self.assertRaisesRegex(model.Refusal,'^session-request-conflict$'):proposal.replay_acquire(saved,bad)
        mutant=self.mutant(proposal,'replay_acquire','session-request-conflict')
        self.assertEqual(mutant['replay_acquire'](saved,request),saved['pin'])
        self.assertEqual(mutant['replay_acquire'](saved,bad),saved['pin'])
        self.assertEqual(saved,before)
        print('plant detected by named vector: changed-generation replay')
        # Removing strict request shape permits an otherwise well-formed unknown key.
        mutant=self.mutant(proposal,'decode_acquire','candidate-acquire-schema')
        self.assertEqual(mutant['decode_acquire'](raw),request)
        self.assertIn('unknown',mutant['decode_acquire'](json.dumps(dict(request,unknown=True))))
        print('plant detected by named vector: candidate-acquire-schema')
        # Disabling duplicate-key rejection must expose the named JSON refusal,
        # using a duplicate of the correct token so shape alone cannot detect it.
        duplicate=raw.replace('"record":', '"record": "'+request['record']+'", "record":',1)
        with self.assertRaisesRegex(model.Refusal,'^candidate-request-json$'):proposal.decode_acquire(duplicate)
        mutant=self.mutant(proposal,'decode_acquire',expression='object_pairs_hook=strict_pairs',replacement='object_pairs_hook=dict')
        self.assertEqual(mutant['decode_acquire'](raw),request);self.assertEqual(mutant['decode_acquire'](duplicate),request)
        print('plant detected by named vector: candidate-request-json')

    def test_policy_cas_and_prune_plants(self):
        # CAS/revision/selected-lock mismatch refuses unchanged; initial enrollment
        # and N+1 update work. Prune requires explicit stop attestation and no edge.
        current=self.base['policy'];valid=deepcopy(current);valid['revision']=2
        selected={p['profile']:p['lock_sha256'] for p in current['profiles']}
        self.assertEqual(proposal.policy_update(None,current,0,selected),current)
        for reason,change,revision in [
            ('policy-update-schema',lambda p:p.update(extra=True),1),
            ('policy-update-cas',lambda p:None,0),
            ('policy-update-revision',lambda p:p.update(revision=1),1),
            ('policy-update-lock',lambda p:p['profiles'][0].update(lock_sha256='f'*64),1)]:
            bad=deepcopy(valid);change(bad);before=deepcopy((current,bad,selected))
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.policy_update(current,bad,revision,selected)
            mutant=self.mutant(proposal,'policy_update',reason)
            self.assertEqual(mutant['policy_update'](current,valid,1,selected),valid)
            self.assertEqual(mutant['policy_update'](current,bad,revision,selected),bad)
            self.assertEqual((current,bad,selected),before)
            print('plant detected by named vector:',reason)
        for reason,args in [('prune-automatic',(True,True,False)),('prune-attestation',(False,False,False)),('prune-retained',(False,True,True))]:
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.prune_candidate(*args)
            mutant=self.mutant(proposal,'prune_candidate',reason)
            self.assertEqual(mutant['prune_candidate'](False,True,False),'operator-prune')
            self.assertEqual(mutant['prune_candidate'](*args),'operator-prune')
            print('plant detected by named vector:',reason)
        # Missing selected profile cannot masquerade as a lock postimage.
        with self.assertRaisesRegex(model.Refusal,'^policy-update-lock$'):proposal.policy_update(current,valid,1,{})
        mutant=self.mutant(proposal,'policy_update',expression="selected.get(p['profile'])",replacement="selected.get(p['profile'], p['lock_sha256'])")
        self.assertEqual(mutant['policy_update'](current,valid,1,selected),valid)
        self.assertEqual(mutant['policy_update'](current,valid,1,{}),valid)
        print('plant detected by named vector: policy-update-missing-selection')
        self.assertEqual(proposal.policy_update(current,valid,1,selected),valid)
        self.assertEqual(proposal.prune_candidate(False,True,False),'operator-prune')

    def test_explicit_pair_transport_scrub_and_plants(self):
        # Supplied matrix.env values/default store lose to nonempty process env
        # unless the recommended explicit-pair removal happens before planning.
        # Matching and unset controls work; no config file or network is used.
        selected=dict(A2A_MATRIX_URL='https://selected.invalid',A2A_MATRIX_SERVER_NAME='selected.invalid',
                      A2A_SECRET_STORE='file',A2A_MATRIX_REGISTRATION_TOKEN='fixture-selected')
        inherited=dict(A2A_MATRIX_URL='https://parent.invalid',A2A_MATRIX_SERVER_NAME='parent.invalid',
                       A2A_SECRET_STORE='keychain',A2A_MATRIX_REGISTRATION_TOKEN='fixture-parent')
        preserved=dict(TMUX='/fixture/tmux,1,0',TMUX_PANE='%7',CLAUDECODE='1',CODEX_SANDBOX='fixture',
                       CODEX_SANDBOX_NETWORK_DISABLED='1',PATH='/usr/bin')
        env=dict(preserved,**inherited);before=deepcopy(env)
        def effective(result):return {key:result.get(key) or value for key,value in selected.items()}
        expected=dict(preserved,A2A_AGENT='agent-one',A2A_CONFIG_DIR='/identities/one/.a2a')
        result=proposal.identity_environment('agent-one','/identities/one',env)
        self.assertEqual(result,expected);self.assertEqual(effective(result),selected)
        for control in [preserved,dict(preserved,**selected),dict(preserved,**{k:'' for k in selected})]:
            self.assertEqual(proposal.identity_environment('agent-one','/identities/one',control),expected)
        self.assertEqual(proposal.identity_environment(None,None,env),env)
        expression="k not in {'A2A_MATRIX_URL','A2A_MATRIX_SERVER_NAME','A2A_SECRET_STORE','A2A_MATRIX_REGISTRATION_TOKEN'}"
        for key in selected:
            mutant=self.mutant(proposal,'identity_environment',expression=expression,
                               replacement='k not in '+repr(set(selected)-{key}))
            self.assertEqual(mutant['identity_environment']('agent-one','/identities/one',preserved),expected)
            bad=mutant['identity_environment']('agent-one','/identities/one',env)
            self.assertEqual(effective(bad)[key],inherited[key]);self.assertNotEqual(effective(bad)[key],selected[key])
            print('plant detected by named vector: native-transport-scrub '+key+' (inherited override survives)')
        self.assertEqual(env,before)

    @staticmethod
    def station_observation():
        # Synthetic no-follow metadata; 32 is a fixture parameter, not an allocated format.
        return dict(path='/managed/home/.a2a', complete=True, exists=True, kind='directory', mode=0o700, uid=1000, entries={
            'courier.sock': dict(kind='file', value='/run/courier/service.sock'),
            'identity': dict(kind='file', value='agent-one'),
            'station.key': dict(kind='file', mode=0o600, size=32)})

    def test_station_link_refusals_and_plants(self):
        # Every failed observation refuses before the carrier step, without
        # echoing values or mutating inputs. Each guard plant admits its own bad
        # validation-stage row and the nearby valid control. Namespace plants
        # exercise the shape helper; no real filesystem/Courier is tested.
        rows = [
            ('directory-location', 'native-station-directory-location', lambda d: d.update(path='/legacy/credentials')),
            ('observation-unreadable', 'native-station-unreadable', lambda d: d.update(complete=False)),
            ('directory-missing', 'native-station-directory-missing', lambda d: d.update(exists=False)),
            ('directory-symlink', 'native-station-directory-type', lambda d: d.update(kind='symlink')),
            ('directory-file', 'native-station-directory-type', lambda d: d.update(kind='file')),
            ('directory-mode', 'native-station-directory-mode', lambda d: d.update(mode=0o755)),
            ('directory-owner', 'native-station-directory-owner', lambda d: d.update(uid=2000)),
            ('credential-looking-extra', 'native-station-extra-entry', lambda d: d['entries'].update({'credentials.json': dict(kind='file', value='do-not-echo-extra')})),
            ('key-mode', 'native-station-key-mode', lambda d: d['entries']['station.key'].update(mode=0o644)),
            ('identity-mismatch', 'native-station-identity', lambda d: d['entries']['identity'].update(value='do-not-echo-identity')),
            ('socket-relative', 'native-station-socket-absolute', lambda d: d['entries']['courier.sock'].update(value='do-not-echo-socket')),
        ]
        for name in ['courier.sock', 'identity', 'station.key']:
            rows.append(('missing-'+name, 'native-station-missing-entry', lambda d, n=name: d['entries'].pop(n)))
            rows.append(('symlink-'+name, 'native-station-entry-type', lambda d, n=name: d['entries'][n].update(kind='symlink')))
        rows.append(('fifo-entry', 'native-station-entry-type', lambda d: d['entries']['courier.sock'].update(kind='fifo')))
        for size in [0, 31, 33]:
            rows.append(('key-size-'+str(size), 'native-station-key-size', lambda d, n=size: d['entries']['station.key'].update(size=n)))
        env = dict(PATH='/usr/bin', A2A_SESSION_ID='parent', A2A_MATRIX_URL='https://parent.invalid')
        expected = dict(PATH='/usr/bin', A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        def launch(link):
            return proposal.native_identity_launch('agent-one', '/managed/home', env, 1000, link, 32)
        for label, reason, change in rows:
            with self.subTest(vector=label, refusal=reason):
                valid = self.station_observation(); bad = deepcopy(valid); change(bad)
                before = deepcopy((valid, bad, env))
                self.assertEqual(launch(valid), expected)
                with patch.object(proposal, 'identity_environment', side_effect=AssertionError('carrier ran before station refusal')):
                    with self.assertRaisesRegex(model.Refusal, '^'+reason+'$'):
                        launch(bad)
                self.assertEqual((valid, bad, env), before)
                if reason in {'native-station-extra-entry', 'native-station-missing-entry'}:
                    # Namespace removal is detected at its own stage, before
                    # downstream value access could mask it with a KeyError.
                    mutant = self.mutant(proposal, 'station_link_entries', reason)
                    self.assertIsNone(mutant['station_link_entries'](valid['entries']))
                    self.assertIsNone(mutant['station_link_entries'](bad['entries']))
                else:
                    mutant = self.mutant(proposal, 'station_link', reason)
                    self.assertEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, valid, 32), expected)
                    self.assertEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, bad, 32), expected)
                self.assertEqual((valid, bad, env), before)
                print('plant detected by named vector: station-link-'+label+' ('+reason+')')

    def test_station_secret_metadata_only_and_unresolved_contract(self):
        # The launcher model consumes only key metadata, never secret contents.
        # An unresolved size contract refuses before delivery; two supplied
        # fixture sizes work and allocate no production size/encoding.
        class SecretMetadata(dict):
            def __getitem__(self, key):
                if key not in {'kind', 'mode', 'size'}:
                    raise AssertionError('station-secret-content-read')
                return super().__getitem__(key)
        link = self.station_observation()
        link['entries']['station.key'] = SecretMetadata(link['entries']['station.key'])
        expected = dict(A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        for size in [32, 64]:
            link['entries']['station.key']['size'] = size
            self.assertEqual(proposal.native_identity_launch('agent-one', '/managed/home', {}, 1000, link, size), expected)
        before = deepcopy(link)
        with self.assertRaisesRegex(model.Refusal, '^native-station-contract-unresolved$'):
            proposal.native_identity_launch('agent-one', '/managed/home', {}, 1000, link, None)
        self.assertEqual(link, before)
        mutant = self.mutant(proposal, 'station_link', expression="key['size']", replacement="len(key['value'])")
        with self.assertRaisesRegex(AssertionError, '^station-secret-content-read$'):
            mutant['native_identity_launch']('agent-one', '/managed/home', {}, 1000, link, 64)
        print('plant detected by named vector: station-secret-content-read')

    def test_native_station_derivation_and_legacy_refusal(self):
        # The removed flag cannot select credentials; an inherited credential
        # directory conflicts with the derived link. No-identity launches still
        # scrub session selectors without requiring station-link observations.
        link = self.station_observation(); env = dict(PATH='/usr/bin', A2A_SESSION_ID='parent')
        before = deepcopy((link, env))
        expected = dict(PATH='/usr/bin', A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        self.assertEqual(proposal.native_identity_launch('agent-one', '/managed/home', env, 1000, link, 32), expected)
        with self.assertRaisesRegex(model.Refusal, '^native-a2a-config-dir-unsupported$'):
            proposal.native_identity_launch('agent-one', '/managed/home', env, 1000, link, 32, legacy_directory_flag=True)
        mutant = self.mutant(proposal, 'native_identity_launch', 'native-a2a-config-dir-unsupported')
        self.assertEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, link, 32), expected)
        self.assertEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, link, 32, legacy_directory_flag=True), expected)
        for key, value in [('A2A_AGENT', 'other'), ('A2A_CONFIG_DIR', '/legacy/credentials')]:
            bad = dict(env, **{key: value}); saved = deepcopy(bad)
            with self.assertRaisesRegex(model.Refusal, '^native-identity-conflict$'):
                proposal.native_identity_launch('agent-one', '/managed/home', bad, 1000, link, 32)
            self.assertEqual(bad, saved)
        self.assertEqual(proposal.native_identity_launch(None, '/managed/home', env, 1000, None, None), dict(PATH='/usr/bin'))
        self.assertEqual((link, env), before)
        print('plant detected by named vector: removed-native-directory-flag')
        # Deriving from the parent of the managed home is a different namespace.
        mutant = self.mutant(proposal, 'identity_environment', expression="managed_home.rstrip('/')+'/.a2a'", replacement="managed_home.rstrip('/').rsplit('/', 1)[0]+'/.a2a'")
        self.assertNotEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, link, 32), expected)
        print('plant detected by named vector: station-link-managed-home-derivation')

    def test_a2a_upgrade_image_and_plant(self):
        # A successful bind/PATH lookup is insufficient: stale hook settings can
        # bind G1 in a G2 session. Supplied image pairs only, no Linux execution.
        old, selected = '8:101', '8:202'
        self.assertEqual(proposal.a2a_upgrade_observation(selected,selected,selected),selected)
        mutant=self.mutant(proposal,'a2a_upgrade_observation','native-a2a-upgrade-image')
        self.assertEqual(mutant['a2a_upgrade_observation'](selected,selected,selected),selected)
        for hooks,consumer in [(old,old),(selected,old),(old,selected)]:
            with self.subTest(hooks=hooks,consumer=consumer):
                with self.assertRaisesRegex(model.Refusal,'^native-a2a-upgrade-image$'):
                    proposal.a2a_upgrade_observation(selected,hooks,consumer)
                self.assertEqual(mutant['a2a_upgrade_observation'](selected,hooks,consumer),consumer)
        print('plant detected by named vector: native-a2a-upgrade-image (stale settings or consumer image)')

    def test_a2a_published_prefix_and_plant(self):
        # The basename rule keeps a published a2a image in the scan's candidate
        # set; it does not execute Linux enumeration or prove image identity.
        for name in ['a2a','a2a-native']:
            proposal.a2a_published_name(name)
        with self.assertRaisesRegex(model.Refusal,'^native-a2a-published-prefix$'):
            proposal.a2a_published_name('renamed-agent')
        mutant=self.mutant(proposal,'a2a_published_name','native-a2a-published-prefix')
        mutant['a2a_published_name']('a2a');mutant['a2a_published_name']('renamed-agent')
        print('plant detected by named vector: native-a2a-published-prefix')

    def test_identity_keys_and_plants(self):
        # Every native launch scrubs three old session keys, accepts empty selectors,
        # and rejects only nonempty mismatches in the two documented identity keys.
        # The directory is derived from the supplied resolved managed home.
        env={'PATH':'/tools:/usr/bin','A2A_SESSION_ID':'old','CODEX_THREAD_ID':'old-thread','CLAUDE_CODE_SESSION_ID':'old-claude'};before=deepcopy(env)
        base={'PATH':env['PATH']};expected=dict(base,A2A_AGENT='agent-one',A2A_CONFIG_DIR='/identities/one/.a2a')
        self.assertEqual(proposal.identity_environment(None,None,env),base)
        self.assertEqual(proposal.identity_environment('agent-one','/identities/one',env),expected)
        self.assertEqual(proposal.identity_environment('agent-one','/identities/one',dict(env,A2A_AGENT='',A2A_CONFIG_DIR='')),expected)
        self.assertEqual(proposal.identity_environment('agent-one','/identities/one',expected),expected)
        self.assertEqual(proposal.identity_environment(None,'/identities/one',env),base)
        for args in [('agent-one',None,env)]:
            with self.assertRaisesRegex(model.Refusal,'^native-identity-pair$'):proposal.identity_environment(*args)
        for reason,args in [
            ('native-identity-pair',('', '/identities/one',env)),
            ('native-identity-directory',('agent-one','relative',env)),
            ('native-identity-conflict',('agent-one','/identities/one',dict(env,A2A_AGENT='other'))),
            ('native-identity-conflict',('agent-one','/identities/one',dict(env,A2A_CONFIG_DIR='/other')))]:
            with self.assertRaisesRegex(model.Refusal,'^'+reason+'$'):proposal.identity_environment(*args)
            mutant=self.mutant(proposal,'identity_environment',reason)
            self.assertEqual(mutant['identity_environment']('agent-one','/identities/one',env),expected)
            mutant['identity_environment'](*args)
            label=reason
            if reason=='native-identity-conflict':label+=' '+('A2A_AGENT' if args[2].get('A2A_AGENT')=='other' else 'A2A_CONFIG_DIR')
            print('plant detected by named vector:',label)
        for key in ['A2A_SESSION_ID','CODEX_THREAD_ID','CLAUDE_CODE_SESSION_ID']:
            expression="k not in {'A2A_SESSION_ID','CODEX_THREAD_ID','CLAUDE_CODE_SESSION_ID'}"
            remaining={'A2A_SESSION_ID','CODEX_THREAD_ID','CLAUDE_CODE_SESSION_ID'}-{key}
            mutant=self.mutant(proposal,'identity_environment',expression=expression,replacement='k not in '+repr(remaining))
            self.assertEqual(mutant['identity_environment']('agent-one','/identities/one',base),expected)
            self.assertNotIn(key,proposal.identity_environment('agent-one','/identities/one',env))
            self.assertIn(key,mutant['identity_environment']('agent-one','/identities/one',env))
            self.assertNotIn(key,proposal.identity_environment(None,None,env))
            self.assertIn(key,mutant['identity_environment'](None,None,env))
            print('plant detected by named vector: native-session-scrub '+key)
        self.assertEqual(env,before)

    def test_a9_fresh_pin_authority_and_plant(self):
        # Single field substitutions refuse; genuine joint revision advance passes.
        # Fixture values do not prove OS observation or independent manager trust.
        ns=self.mutant(model,'pin_authority',expression='pin[field] == authority[field]')
        for section,check in [('launchers',model.launcher_check),('sessions',model.session_check)]:
            for case in fixtures.output()[section]:
                before=deepcopy(case['state'])
                self.assertEqual(model.decision(check,case['state']),(case['expected'],case['reason']),case['id'])
                self.assertEqual(case['state'],before)
                if case['id'] in {'launcher-valid','launcher-next-revision'}:
                    self.assertEqual(ns['decision'](ns['launcher_check'],case['state']),('accept','verified'))
                if section=='launchers' and case['id'] in {'launcher-session-'+n for n in ['revision','supervisor','boot','domain','start','request']} | {'launcher-authority-unknown'}:
                    self.assertEqual(ns['decision'](ns['launcher_check'],case['state']),('accept','verified'))
                    print('plant detected by named vector:',case['id'])

    def test_a10_restore_guards_and_plants(self):
        # Distinct plain/live/unknown inputs preserve old edges and all preimages
        # on refusal. Each observer/operator/reason clause has its own negative.
        rows={c['id']:c for c in fixtures.output()['transactions']}
        self.assertEqual([rows[n]['state']['retained_edge']['kind'] for n in ['repair-explicit','repair-pinned-restore','repair-stale-session']],['none','live-session','unknown-session'])
        for case in rows.values():
            before=deepcopy(case['state']);actual=model.transaction(case['state'])
            self.assertEqual(actual,case['expected'],case['id']);self.assertEqual(case['state'],before)
            self.assertEqual(actual['retained_edge'],before['retained_edge'])
            if actual['outcome']=='refuse-unchanged':self.assertEqual(actual['live'],before['before'])
        for expression,row,control,replacement in [
            ("edge['kind'] == 'unknown-session'",'repair-stale-session','repair-pinned-restore','False'),
            ("state['staged_edge'] != edge",'repair-retargeted','repair-pinned-restore','False'),
            ("state['audit_durable']",'repair-stale-unaudited','repair-stale-broken','True'),
            ("state['if_revision'] == edge['revision']",'repair-stale-revision','repair-stale-broken','True'),
            ("state['descendants_quiescent']",'repair-stale-descendant','repair-stale-reconciled','True'),
            ("state['observer_confirmed']",'repair-stale-observer','repair-stale-reconciled','True'),
            ("state['operator']",'repair-stale-operator','repair-stale-broken','True'),
            ("bool(state['reason'])",'repair-stale-reason','repair-stale-broken','True')]:
            mutant=self.mutant(model,'transaction',expression=expression,replacement=replacement)
            self.assertEqual(mutant['transaction'](rows[control]['state']),rows[control]['expected'])
            self.assertEqual(model.transaction(rows[row]['state']),rows[row]['expected'])
            changed=mutant['transaction'](rows[row]['state'])
            self.assertEqual(changed['outcome'],'fresh-generation-preserve-old')
            self.assertEqual(changed['refusal'],'')
            print('plant detected by named vector:',row)

    def test_actual_gate_rows_and_plants(self):
        # Each actual CLOSED packet row is checked; changing it to OPEN or deleting
        # it fails by that row's name. This is text consistency, not acceptance.
        text=(model.ROOT/'protocol/profile-command-root-admission.md').read_text(encoding='utf-8')
        proposal.check_gate_text(text)
        # A cp1252 default must still decode the actual UTF-8 packet. The
        # explicit wrong-codec plant fails by decoding, not by a model verdict.
        read_text=Path.read_text
        packet=model.ROOT/'protocol/profile-command-root-admission.md'
        def cp1252_default(path, encoding=None, **kwargs):
            return read_text(path, encoding=encoding or ('cp1252' if path == packet else 'utf-8'), **kwargs)
        with patch.object(Path, 'read_text', cp1252_default):
            proposal.validate()
            wrong_codec=self.mutant(proposal,'validate',expression="(ROOT/'protocol/profile-command-root-admission.md').read_text(encoding='utf-8')",replacement="(ROOT/'protocol/profile-command-root-admission.md').read_text(encoding='cp1252')")
            with self.assertRaises(UnicodeDecodeError) as failure:wrong_codec['validate']()
            self.assertEqual(failure.exception.reason,'character maps to <undefined>')
        print('encoding regression plant detected: packet-utf8-read (intended wrong-codec decode failure)')
        mutant=self.mutant(proposal,'check_gate_text',expression="len(rows) == 1 and rows[0].startswith('| '+gate+' — **CLOSED** |')")
        mutant['check_gate_text'](text)
        for gate in proposal.GATES:
            changed=text.replace('| '+gate+' — **CLOSED** |','| '+gate+' — **OPEN** |')
            with self.assertRaisesRegex(model.Refusal,'^gate-status-'+gate+'$'):proposal.check_gate_text(changed)
            mutant['check_gate_text'](changed)
            missing='\n'.join(line for line in text.splitlines() if not line.startswith('| '+gate+' — '))
            with self.assertRaisesRegex(model.Refusal,'^gate-status-'+gate+'$'):proposal.check_gate_text(missing)
            mutant['check_gate_text'](missing)
            print('plant detected by named vector: gate-status-'+gate)

    def test_gate_inventory_and_roots_plants(self):
        # Shrinking the inventory refuses; every named roots/hook declaration
        # refuses OPEN or absence. Positive controls prevent reject-all success.
        text=(model.ROOT/'protocol/profile-command-root-admission.md').read_text(encoding='utf-8')
        mutant=self.mutant(proposal,'check_gate_text','gate-inventory')
        mutant['check_gate_text'](text)
        with patch.object(proposal,'GATES',proposal.GATES[:-1]):
            with self.assertRaisesRegex(model.Refusal,'^gate-inventory$'):proposal.check_gate_text(text)
            mutant['GATES']=proposal.GATES;mutant['check_gate_text'](text)
        print('plant detected by named vector: gate-inventory')
        roots=(model.ROOT/'protocol/profile-command-roots.md').read_text(encoding='utf-8')
        proposal.check_root_gate_text(roots)
        mutant=self.mutant(proposal,'check_root_gate_text',expression="len(rows) == 1 and rows[0].startswith('**CLOSED '+marker)")
        mutant['check_root_gate_text'](roots)
        lines=[l for l in roots.splitlines() if l.startswith('**CLOSED ') and ' gate — ' in l]
        self.assertEqual(len(lines),8)
        for line in lines:
            name=line.split(' gate — ',1)[1].split(':**',1)[0]
            for changed in [roots.replace(line,line.replace('**CLOSED ','**OPEN ',1)),roots.replace(line,'')]:
                with self.assertRaisesRegex(model.Refusal,'^roots-gate-status-'+name+'$'):proposal.check_root_gate_text(changed)
                mutant['check_root_gate_text'](changed)
            print('plant detected by named vector: roots-gate-status-'+name)


if __name__=='__main__':unittest.main()
