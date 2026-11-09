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
    def courier_contract():
        # Supplied a2a package courier constants, not an implemented module pin.
        return dict(ProtocolVersion=1, StationKeyLen=32)

    @staticmethod
    def station_observation():
        # Synthetic no-follow metadata; supplied a2a enroll contract length is 32 bytes.
        return dict(path='/managed/home/.a2a', resolved_path='/managed/home/.a2a', complete=True, exists=True, kind='directory', mode=0o700, uid=1000, resolution=dict(requested_home='/managed/home', canonical_home='/managed/home',
            ancestors=[
                dict(path='/', kind='directory', uid=0, mode=0o755),
                dict(path='/managed', kind='directory', uid=0, mode=0o755),
                dict(path='/managed/home', kind='directory', uid=1000, mode=0o700)]), entries={
            'courier.sock': dict(kind='file', uid=1000, mode=0o600, nlink=1, value=b'/run/courier/service.sock\n'),
            'identity': dict(kind='file', uid=1000, mode=0o600, nlink=1, value='agent-one\n'),
            'station': dict(kind='file', uid=1000, mode=0o600, nlink=1, value='station-one\n'),
            'station.key': proposal.StationKeyMetadata(kind='file', uid=1000, mode=0o600, size=32, nlink=1)})

    def test_canonical_station_home_vectors_and_plant(self):
        # Supplied EvalSymlinks facts admit an aliased home after canonicalization.
        # Unsafe ancestors and link/entry symlinks refuse before delivery without
        # input writes. A canonical result must be bound to the requested input
        # home and absolute. This proves bounded checks, not live OS resolution.
        alias = '/alias/home'
        def aliased():
            link = self.station_observation()
            link['resolution']['requested_home'] = alias
            return link
        rows = [
            ('group-writable-parent', 'native-station-ancestor-writable', lambda d: d['resolution']['ancestors'][1].update(mode=0o775)),
            ('world-writable-parent', 'native-station-ancestor-writable', lambda d: d['resolution']['ancestors'][1].update(mode=0o757)),
            ('foreign-owned-parent', 'native-station-ancestor-owner', lambda d: d['resolution']['ancestors'][1].update(uid=2000)),
            ('caller-owned-sticky-writable', 'native-station-ancestor-writable', lambda d: d['resolution']['ancestors'][1].update(uid=1000, mode=0o1777)),
            ('root-owned-home', 'native-station-home-owner', lambda d: d['resolution']['ancestors'][-1].update(uid=0)),
            ('group-writable-home', 'native-station-ancestor-writable', lambda d: d['resolution']['ancestors'][-1].update(mode=0o770)),
            ('unavailable-resolution', 'native-station-home-resolution', lambda d: d.pop('resolution')),
            ('requested-home-mismatch', 'native-station-home-resolution', lambda d: d['resolution'].update(requested_home='/other/input-home')),
            ('relative-canonical-home', 'native-station-home-resolution', lambda d: d['resolution'].update(canonical_home='managed/home')),
            ('omitted-canonical-ancestor', 'native-station-ancestor-observation', lambda d: d['resolution']['ancestors'].pop(1)),
            ('symlink-canonical-ancestor', 'native-station-ancestor-observation', lambda d: d['resolution']['ancestors'][1].update(kind='symlink')),
            ('station-directory-symlink', 'native-station-directory-type', lambda d: d.update(kind='symlink')),
        ]
        for name in ['courier.sock', 'identity', 'station', 'station.key']:
            rows.append(('station-entry-symlink-'+name, 'native-station-entry-type',
                         lambda d, n=name: setattr(d['entries'][n], 'kind', 'symlink') if n == 'station.key' else d['entries'][n].update(kind='symlink')))
        env = dict(A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a', A2A_SESSION_ID='parent')
        expected = dict(A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        def launch(link):
            return proposal.native_identity_launch('agent-one', alias, env, 1000, link, self.courier_contract())
        for label, reason, change in rows:
            with self.subTest(vector=label):
                valid = aliased(); sticky = aliased(); caller = aliased()
                sticky['resolution']['ancestors'][1].update(uid=0, mode=0o1777)
                caller['resolution']['ancestors'][1].update(uid=1000, mode=0o755)
                for control in [valid, sticky, caller]:
                    before = deepcopy((control, env))
                    self.assertEqual(launch(control), expected)
                    self.assertEqual((control, env), before)
                bad = aliased(); change(bad); before = deepcopy((bad, env))
                with patch.object(proposal, 'identity_environment', wraps=proposal.identity_environment) as carrier:
                    with self.assertRaisesRegex(proposal.StationRegistrationRefusal,
                            '^native-environment-not-registered:'+reason+'$'):
                        launch(bad)
                    carrier.assert_not_called()
                self.assertEqual((bad, env), before)
        # Dropping the group/world-write guard admits the named bad vector;
        # owner-safe and root-sticky controls still pass. No unrelated failure.
        valid = aliased(); bad = aliased()
        bad['resolution']['ancestors'][1]['mode'] = 0o775
        before = deepcopy(bad)
        mutant = self.mutant(proposal, 'canonical_station_home', 'native-station-ancestor-writable')
        for control in [valid, sticky]:
            self.assertEqual(mutant['native_identity_launch']('agent-one', alias, env, 1000, control, self.courier_contract()), expected)
        self.assertEqual(mutant['native_identity_launch']('agent-one', alias, env, 1000, bad, self.courier_contract()), expected)
        self.assertEqual(bad, before)
        print('plant detected by named vector: group-writable-parent (native-station-ancestor-writable)')

    def test_station_directory_canonical_readers_and_plant(self):
        # Supplied directory EvalSymlinks observations reject relative and aliased
        # reader paths before delivery, without writes or path reflection. The
        # canonical form of the same aliased home passes; no stored path is used.
        alias = '/alias/home'
        env = dict(A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        def valid():
            link = self.station_observation()
            link['resolution']['requested_home'] = alias
            return link
        def launch(link):
            return proposal.native_identity_launch('agent-one', alias, env, 1000, link, self.courier_contract())
        rows = [
            ('uncanonicalized-ancestor-alias', 'native-station-directory-noncanonical',
             lambda d: d.update(path='/alias/home/.a2a')),
            ('relative-directory', 'native-station-directory-absolute',
             lambda d: d.update(path='home/.a2a')),
            ('resolution-unavailable', 'native-station-directory-resolution',
             lambda d: d.pop('resolved_path')),
            ('path-later-noncanonical', 'native-station-directory-noncanonical',
             lambda d: d.update(resolved_path='/other/home/.a2a')),
        ]
        for label, reason, change in rows:
            with self.subTest(vector=label):
                control = valid(); before = deepcopy((control, env))
                self.assertEqual(launch(control), env)
                self.assertEqual((control, env), before)
                # Already canonical input is the same positive with no alias.
                canonical = self.station_observation(); before_canonical = deepcopy(canonical)
                self.assertEqual(proposal.native_identity_launch('agent-one', '/managed/home', env,
                    1000, canonical, self.courier_contract()), env)
                self.assertEqual(canonical, before_canonical)
                bad = valid(); change(bad); before = deepcopy((bad, env))
                with patch.object(proposal, 'identity_environment', wraps=proposal.identity_environment) as carrier:
                    with self.assertRaisesRegex(proposal.StationRegistrationRefusal,
                            '^native-environment-not-registered:'+reason+'$') as error:
                        launch(bad)
                    carrier.assert_not_called()
                self.assertEqual(str(error.exception), 'native-environment-not-registered:'+reason)
                self.assertEqual((bad, env), before)
        # Removing equality admits a path that became noncanonical despite a
        # still-valid canonical-home observation; its canonical neighbour passes.
        mutant = self.mutant(proposal, 'station_link', 'native-station-directory-noncanonical')
        bad = valid(); bad['resolved_path'] = '/other/home/.a2a'; before = deepcopy(bad)
        for control in [valid(), bad]:
            self.assertEqual(mutant['native_identity_launch']('agent-one', alias, env,
                1000, control, self.courier_contract()), env)
        self.assertEqual(bad, before)
        print('plant detected by named vector: path-later-noncanonical (native-station-directory-noncanonical)')

    def test_station_link_refusals_and_plants(self):
        # Every failed observation refuses before the carrier step, without
        # echoing values or mutating inputs. Each guard plant admits its own bad
        # validation-stage row and the nearby valid control. Namespace plants
        # exercise the shape helper; no real filesystem/Courier is tested.
        rows = [
            ('directory-location', 'native-station-directory-location', lambda d: d.update(path='/legacy/credentials', resolved_path='/legacy/credentials')),
            ('observation-unreadable', 'native-station-unreadable', lambda d: d.update(complete=False)),
            ('directory-missing', 'native-station-directory-missing', lambda d: d.update(exists=False)),
            ('directory-symlink', 'native-station-directory-type', lambda d: d.update(kind='symlink')),
            ('directory-file', 'native-station-directory-type', lambda d: d.update(kind='file')),
            ('directory-mode', 'native-station-directory-mode', lambda d: d.update(mode=0o755)),
            ('directory-owner', 'native-station-directory-owner', lambda d: d.update(uid=2000)),
            ('credential-looking-extra', 'native-station-extra-entry', lambda d: d['entries'].update({'credentials.json': dict(kind='file', value='do-not-echo-extra')})),
            ('key-mode', 'native-station-key-mode', lambda d: setattr(d['entries']['station.key'], 'mode', 0o644)),
            ('identity-mismatch', 'native-station-identity', lambda d: d['entries']['identity'].update(value='do-not-echo-identity\n')),
        ]
        for name in ['courier.sock', 'identity', 'station', 'station.key']:
            rows.append(('missing-'+name, 'native-station-missing-entry', lambda d, n=name: d['entries'].pop(n)))
            rows.append(('owner-'+name, 'native-station-entry-owner', lambda d, n=name: setattr(d['entries'][n], 'uid', 2000) if n == 'station.key' else d['entries'][n].update(uid=2000)))
            rows.append(('symlink-'+name, 'native-station-entry-type', lambda d, n=name: setattr(d['entries'][n], 'kind', 'symlink') if n == 'station.key' else d['entries'][n].update(kind='symlink')))
        rows.append(('fifo-entry', 'native-station-entry-type', lambda d: d['entries']['courier.sock'].update(kind='fifo')))
        for size in [0, 31, 33]:
            rows.append(('key-size-'+str(size), 'native-station-key-size', lambda d, n=size: setattr(d['entries']['station.key'], 'size', n)))
        for mode in [0o500, 0o300, 0o711]:
            rows.append(('directory-mode-'+oct(mode), 'native-station-directory-mode', lambda d, m=mode: d.update(mode=m)))
        for mode in [0o400, 0o640]:
            rows.append(('key-mode-'+oct(mode), 'native-station-key-mode', lambda d, m=mode: setattr(d['entries']['station.key'], 'mode', m)))
        # Exact single-link/0600 rules include owner-only 0400/0700 refusals;
        # both new codes use the same valid-neighbour and in-tree guard plants.
        for name in ['courier.sock', 'identity', 'station', 'station.key']:
            rows.append(('nlink-2-'+name, 'native-station-entry-links',
                lambda d, n=name: setattr(d['entries'][n], 'nlink', 2) if n == 'station.key'
                    else d['entries'][n].update(nlink=2)))
        for name in ['courier.sock', 'identity', 'station']:
            for mode in [0o644, 0o640, 0o400, 0o700]:
                rows.append(('mode-'+oct(mode)+'-'+name, 'native-station-entry-mode',
                    lambda d, n=name, m=mode: d['entries'][n].update(mode=m)))
        env = dict(PATH='/usr/bin', A2A_SESSION_ID='parent', A2A_MATRIX_URL='https://parent.invalid')
        expected = dict(PATH='/usr/bin', A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        def launch(link):
            return proposal.native_identity_launch('agent-one', '/managed/home', env, 1000, link, self.courier_contract())
        for label, reason, change in rows:
            with self.subTest(vector=label, refusal=reason):
                valid = self.station_observation(); bad = deepcopy(valid); change(bad)
                before = deepcopy((valid, bad, env))
                self.assertEqual(launch(valid), expected)
                with patch.object(proposal, 'identity_environment', wraps=proposal.identity_environment) as carrier:
                    with self.assertRaisesRegex(proposal.StationRegistrationRefusal, '^native-environment-not-registered:'+reason+'$') as refusal:
                        launch(bad)
                    carrier.assert_not_called()
                self.assertEqual(refusal.exception.code, 'native-environment-not-registered')
                self.assertEqual(refusal.exception.subreason, reason)
                self.assertEqual((valid, bad, env), before)
                if reason in {'native-station-extra-entry', 'native-station-missing-entry'}:
                    # Namespace removal is detected at its own stage, before
                    # downstream value access could mask it with a KeyError.
                    mutant = self.mutant(proposal, 'station_link_entries', reason)
                    self.assertIsNone(mutant['station_link_entries'](valid['entries']))
                    self.assertIsNone(mutant['station_link_entries'](bad['entries']))
                    if label == 'missing-station':
                        # Only station becomes optional; the allowed set stays
                        # four entries. This plant proves the namespace guard.
                        optional = self.mutant(proposal, 'station_link_entries',
                            expression='names - set(entries)',
                            replacement="(names - {'station'}) - set(entries)")
                        self.assertIsNone(optional['station_link_entries'](valid['entries']))
                        self.assertIsNone(optional['station_link_entries'](bad['entries']))
                else:
                    mutant = self.mutant(proposal, 'station_link', reason)
                    self.assertEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, valid, self.courier_contract()), expected)
                    self.assertEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, bad, self.courier_contract()), expected)
                self.assertEqual((valid, bad, env), before)
                print('plant detected by named vector: station-link-'+label+' ('+reason+')')

    def test_pre_station_three_file_namespace_refusal(self):
        # A pre-station three-file namespace is incomplete, beside a valid
        # four-file control. This targets namespace admission before value reads;
        # the full-launch missing-station row above proves the wrapped refusal.
        valid = self.station_observation()['entries']
        legacy = deepcopy(valid); legacy.pop('station')
        self.assertEqual(set(valid), {'courier.sock', 'identity', 'station', 'station.key'})
        self.assertEqual(set(legacy), {'courier.sock', 'identity', 'station.key'})
        before = deepcopy((valid, legacy))
        self.assertIsNone(proposal.station_link_entries(valid))
        with self.subTest(vector='pre-station-three-file-directory'):
            with self.assertRaisesRegex(proposal.Refusal, '^native-station-missing-entry$'):
                proposal.station_link_entries(legacy)
        self.assertEqual((valid, legacy), before)

    def test_station_registry_name_vectors_and_plants(self):
        # Registry station grammar is checked without delivering the name.
        # Malformed names refuse unchanged before the carrier; distinct valid
        # station names at both length boundaries produce only the identity pair.
        rows = [
            ('space', 'station one\n'), ('uppercase', 'Station-one\n'),
            ('65-characters', 's'*65+'\n'), ('missing-lf', 'station-one'),
            ('two-lines', 'station-one\nother\n'), ('bom', '\ufeffstation-one\n'),
        ]
        expected = dict(A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        def launch(link):
            return proposal.native_identity_launch('agent-one', '/managed/home', {},
                1000, link, self.courier_contract())
        for label, raw in rows:
            with self.subTest(vector='station-name-'+label):
                for name in ['a', 'station._=-09', 's'*64]:
                    valid = self.station_observation(); valid['entries']['station']['value'] = name+'\n'
                    before = deepcopy(valid)
                    with patch.object(proposal, 'identity_environment', wraps=proposal.identity_environment) as carrier:
                        self.assertEqual(launch(valid), expected)
                        carrier.assert_called_once_with('agent-one', '/managed/home', {})
                    self.assertEqual(valid, before)
                bad = self.station_observation(); bad['entries']['station']['value'] = raw
                before = deepcopy(bad)
                with patch.object(proposal, 'identity_environment', wraps=proposal.identity_environment) as carrier:
                    with self.assertRaisesRegex(proposal.StationRegistrationRefusal,
                            '^native-environment-not-registered:native-station-name-format$'):
                        launch(bad)
                    carrier.assert_not_called()
                self.assertEqual(bad, before)
                mutant = self.mutant(proposal, 'station_link', 'native-station-name-format')
                for control in [valid, bad]:
                    self.assertEqual(mutant['native_identity_launch']('agent-one', '/managed/home', {},
                        1000, control, self.courier_contract()), expected)
                self.assertEqual(bad, before)
                print('plant detected by named vector: station-name-'+label+' (native-station-name-format)')

    def test_station_identity_line_vectors_and_plants(self):
        # Exact one-line ASCII identity grammar refuses before delivery, even
        # when the malformed name matches the selected identity. Valid neighbours
        # include both length boundaries; no value is echoed or input changed.
        rows = [
            ('space', 'agent one', 'agent one\n'),
            ('bom', '\ufeffagent-one', '\ufeffagent-one\n'),
            ('uppercase', 'Agent-one', 'Agent-one\n'),
            ('65-characters', 'a'*65, 'a'*65+'\n'),
            ('missing-newline', 'agent-one', 'agent-one'),
            ('two-lines', 'agent-one\nother', 'agent-one\nother\n'),
        ]
        for label, selected, raw in rows:
            with self.subTest(vector=label):
                for name in ['a', 'agent._=-09', 'a'*64]:
                    valid = self.station_observation()
                    valid['entries']['identity']['value'] = name+'\n'
                    expected = dict(A2A_AGENT=name, A2A_CONFIG_DIR='/managed/home/.a2a')
                    self.assertEqual(proposal.native_identity_launch(name, '/managed/home', {}, 1000, valid, self.courier_contract()), expected)
                bad = self.station_observation(); bad['entries']['identity']['value'] = raw
                before = deepcopy(bad)
                with patch.object(proposal, 'identity_environment', wraps=proposal.identity_environment) as carrier:
                    with self.assertRaisesRegex(proposal.StationRegistrationRefusal,
                            '^native-environment-not-registered:native-station-identity-format$'):
                        proposal.native_identity_launch(selected, '/managed/home', {}, 1000, bad, self.courier_contract())
                    carrier.assert_not_called()
                self.assertEqual(bad, before)
                mutant = self.mutant(proposal, 'station_link', 'native-station-identity-format')
                # Kill the format guard at its validation stage. Missing newline
                # is sliced for equality here; choose its mutant selected value
                # to keep that later independent check from masking the plant.
                mutant_selected = raw[:-1]
                self.assertEqual(mutant['station_link']('/managed/home', 'a'*64, 1000, valid, self.courier_contract()), '/managed/home/.a2a')
                self.assertEqual(mutant['station_link']('/managed/home', mutant_selected, 1000, bad, self.courier_contract()), '/managed/home/.a2a')
                self.assertEqual(bad, before)
                print('plant detected by named vector: station-identity-'+label+' (native-station-identity-format)')

    def test_courier_socket_bytes_vectors_and_plants(self):
        # Courier v1 accepts UTF-8 P+LF at 1/103 bytes, including non-ASCII;
        # malformed/overlong files refuse by a content-free sub-reason before
        # delivery, preserving all observations. No filesystem is exercised.
        valid_values = [b'/\n', b'/'+b'a'*102+b'\n', ('/'+'é'*51+'\n').encode('utf-8')]
        rows = [
            ('ascii-104-bytes', b'/'+b'a'*103+b'\n', 'native-station-socket-length'),
            ('unicode-105-bytes', ('/'+'é'*52+'\n').encode('utf-8'), 'native-station-socket-length'),
            ('crlf', b'/path\r\n', 'native-station-socket-line'),
            ('embedded-lf', b'/path\nother\n', 'native-station-socket-line'),
            ('nul', b'/path\x00other\n', 'native-station-socket-line'),
            ('bom', '/\ufeffpath\n'.encode('utf-8'), 'native-station-socket-line'),
            ('leading-bom', '\ufeff/path\n'.encode('utf-8'), 'native-station-socket-line'),
            ('missing-lf', b'/path', 'native-station-socket-line'),
            ('empty-file', b'', 'native-station-socket-line'),
            ('empty-path', b'\n', 'native-station-socket-length'),
            ('relative', b'relative\n', 'native-station-socket-absolute'),
            ('invalid-utf8', b'/path\xff\n', 'native-station-socket-utf8'),
        ]
        def launch(raw):
            link = self.station_observation(); link['entries']['courier.sock']['value'] = raw
            before = deepcopy(link)
            try:
                return proposal.native_identity_launch('agent-one', '/managed/home', {}, 1000, link, self.courier_contract())
            finally:
                self.assertEqual(link, before)
        expected = dict(A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        for label, raw, reason in rows:
            with self.subTest(vector=label):
                for control in valid_values:
                    self.assertEqual(launch(control), expected)
                with patch.object(proposal, 'identity_environment', wraps=proposal.identity_environment) as carrier:
                    with self.assertRaisesRegex(proposal.StationRegistrationRefusal,
                            '^native-environment-not-registered:'+reason+'$'):
                        launch(raw)
                    carrier.assert_not_called()
        # Independent plants target the explicit byte bound, UTF-8 decoder and
        # line/absolute checks. Each retains every valid control.
        for label, raw, reason, expression, replacement in [
            ('byte-bound', rows[1][1], 'native-station-socket-length', "len(path.encode('utf-8'))", 'len(path)'),
            ('crlf', rows[2][1], 'native-station-socket-line', "not any(c in path for c in ('\\x00', '\\r', '\\n', '\\ufeff'))", 'True'),
            ('relative', b'relative\n', 'native-station-socket-absolute', None, None),
            ('utf8', b'/path\xff\n', 'native-station-socket-utf8', "errors='strict'", "errors='replace'")]:
            if expression:
                mutant = self.mutant(proposal, 'courier_socket_path', expression=expression, replacement=replacement)
            else:
                mutant = self.mutant(proposal, 'courier_socket_path', reason)
            for control in valid_values:
                self.assertEqual(mutant['courier_socket_path'](control), control[:-1].decode('utf-8'))
            mutant['courier_socket_path'](raw)
            print('plant detected by named vector: courier-socket-'+label+' ('+reason+')')
        # P9 was a valid LF-file probe, not a mutant. Keep it admitted and kill
        # the old whole-file absolute() check that incorrectly rejected its LF.
        raw = b'/run/courier/service.sock\n'
        self.assertEqual(launch(raw), expected)
        old = self.mutant(proposal, 'courier_socket_path', expression='return path',
                         replacement="require(absolute(text), 'native-station-socket-absolute')\n    return path")
        with self.assertRaisesRegex(model.Refusal, '^native-station-socket-absolute$'):
            old['courier_socket_path'](raw)
        print('plant detected by named vector: P9-old-whole-file-absolute-refusal')

    def test_station_secret_metadata_only_and_unresolved_contract(self):
        # Only metadata attributes are exposed. Attribute, get and iteration
        # secret-read plants fail explicitly, with a valid launch beside them.
        class SecretMetadata(proposal.StationKeyMetadata):
            __slots__ = ()

            def __getattr__(self, name):
                if name.startswith('__'):
                    raise AttributeError(name)
                raise AssertionError('station-secret-content-read')

            def __iter__(self):
                raise AssertionError('station-secret-content-read')

        link = self.station_observation()
        link['entries']['station.key'] = SecretMetadata(kind='file', uid=1000, mode=0o600, size=32, nlink=1)
        expected = dict(A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        before = deepcopy(link)
        self.assertEqual(proposal.native_identity_launch('agent-one', '/managed/home', {}, 1000, link, self.courier_contract()), expected)
        for contract in [None, {}, dict(ProtocolVersion=1), dict(ProtocolVersion=2, StationKeyLen=32)]:
            with self.subTest(contract=contract):
                with self.assertRaisesRegex(proposal.StationRegistrationRefusal, '^native-environment-not-registered:native-station-contract-unresolved$'):
                    proposal.native_identity_launch('agent-one', '/managed/home', {}, 1000, link, contract)
                self.assertEqual(link, before)
        for label, expression in [('attribute', 'key.value'), ('get', "key.get('value')"),
                                  ('iteration', 'list(key)'), ('items', 'key.items()'),
                                  ('values', 'key.values()')]:
            mutant = self.mutant(proposal, 'station_link', expression="    key = entries['station.key']",
                                 replacement="    key = entries['station.key']\n    _probe = "+expression)
            with self.assertRaisesRegex(AssertionError, '^station-secret-content-read$'):
                mutant['native_identity_launch']('agent-one', '/managed/home', {}, 1000, link, self.courier_contract())
            self.assertEqual(link, before)
            print('plant detected by named vector: station-secret-content-read-'+label)

    def test_native_station_derivation_and_legacy_refusal(self):
        # The removed flag cannot select credentials; an inherited credential
        # directory conflicts with the derived link. No-identity launches still
        # scrub session selectors without requiring station-link observations.
        link = self.station_observation(); env = dict(PATH='/usr/bin', A2A_SESSION_ID='parent')
        before = deepcopy((link, env))
        expected = dict(PATH='/usr/bin', A2A_AGENT='agent-one', A2A_CONFIG_DIR='/managed/home/.a2a')
        self.assertEqual(proposal.native_identity_launch('agent-one', '/managed/home', env, 1000, link, self.courier_contract()), expected)
        with self.assertRaisesRegex(model.Refusal, '^native-a2a-config-dir-unsupported$'):
            proposal.native_identity_launch('agent-one', '/managed/home', env, 1000, link, self.courier_contract(), legacy_directory_flag=True)
        mutant = self.mutant(proposal, 'native_identity_launch', 'native-a2a-config-dir-unsupported')
        self.assertEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, link, self.courier_contract()), expected)
        self.assertEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, link, self.courier_contract(), legacy_directory_flag=True), expected)
        for key, value in [('A2A_AGENT', 'other'), ('A2A_CONFIG_DIR', '/legacy/credentials')]:
            bad = dict(env, **{key: value}); saved = deepcopy(bad)
            with self.assertRaisesRegex(model.Refusal, '^native-identity-conflict$'):
                proposal.native_identity_launch('agent-one', '/managed/home', bad, 1000, link, self.courier_contract())
            self.assertEqual(bad, saved)
        self.assertEqual(proposal.native_identity_launch(None, '/managed/home', env, 1000, None, None), dict(PATH='/usr/bin'))
        self.assertEqual((link, env), before)
        print('plant detected by named vector: removed-native-directory-flag')
        # Deriving from the parent of the managed home is a different namespace.
        mutant = self.mutant(proposal, 'identity_environment', expression="managed_home.rstrip('/')+'/.a2a'", replacement="managed_home.rstrip('/').rsplit('/', 1)[0]+'/.a2a'")
        self.assertNotEqual(mutant['native_identity_launch']('agent-one', '/managed/home', env, 1000, link, self.courier_contract()), expected)
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
