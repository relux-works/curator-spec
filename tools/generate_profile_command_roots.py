"""Deterministic bounded specification fixtures, never runtime qualification."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def seal(s, inventory=None, receipt=None, marker=None):
    t=s['trusted']; o=s['observed']; b=s['fragment']['command_root']
    inventory=json.loads(t['inventory']) if inventory is None else inventory
    receipt=json.loads(t['receipt']) if receipt is None else receipt
    marker=json.loads(t['marker']) if marker is None else marker
    b['inventory_sha256']=digest(canonical(inventory))
    receipt['binding']['inventory_sha256']=marker['binding']['inventory_sha256']=b['inventory_sha256']
    b['receipt_sha256']=digest(canonical(receipt)); marker['receipt_sha256']=b['receipt_sha256']
    b['marker_sha256']=digest(canonical(marker)); t['binding']=deepcopy(b)
    for key,value in [('inventory',inventory),('receipt',receipt),('marker',marker)]:
        t[key]=o[key]=canonical(value)


def fixture(profile='work', version='one', manager='/m', platform='linux-amd64', script=False, name='a2a'):
    windows=platform.startswith('windows-')
    if windows and manager=='/m': manager='C:/m'
    lock=digest(profile+version); generation=digest('generation'+profile+version)
    root=manager+'/environments/'+profile+'/commands/'+generation+'/'+platform+'/bin'
    b=dict(lock_sha256=lock,plan_sha256=digest('plan'+version),generation=generation,platform=platform,
           receipt_sha256='0'*64,marker_sha256='0'*64,inventory_sha256='0'*64)
    base={k:v for k,v in b.items() if k not in ['receipt_sha256','marker_sha256']}
    owner='sid:S-1-5-21' if windows else 'uid:1000'; dacl='sha256:'+digest('private')
    def meta(label, mode):
        m=dict(platform='windows' if windows else 'posix',owner=owner,filesystem_id='volume:1' if windows else 'device:1',object_id=digest(profile+version+label))
        m.update(security_descriptor_sha256=dacl) if windows else m.update(mode=mode)
        return m
    rootmeta=meta('root',0o700)
    paths=[root+'/'+name]
    if windows: paths=[root+'/'+name+'.cmd',root+'/'+name+'.exe']
    elif script: paths=[root+'/'+name,manager+'/interpreters/fixed']
    files={}; chain=[]
    for i,path in enumerate(paths):
        terminal=i==len(paths)-1; target=None if terminal else paths[i+1]
        content='native '+version if terminal else 'FIXTURE-FORWARD/1\n'+target+'\n'
        m=meta(path,0o500)
        files[path]=dict(kind='regular',links=1,bytes=content,size=len(content.encode()),format='native' if terminal else 'forwarder',**{k:v for k,v in m.items() if k!='platform'})
        chain.append(dict(path=path,kind='executable' if terminal else 'forwarder',metadata=m,sha256='sha256:'+digest(content),target=target))
    inventory=dict(record='profile-command-inventory/1',root=dict(path=root,metadata=rootmeta),commands=[dict(name=name,chain=chain)])
    receipt=dict(record='profile-command-root/2',profile=profile,binding=deepcopy(base),commands=[dict(name=name,source='https://example.org/skill',commit=digest('commit'+version)[:40],directory='.',driver='go-repository-v1',artifact_receipt_sha256=digest('artifact'+version),executable_sha256=digest('native '+version))])
    marker=dict(record='profile-command-generation/1',profile=profile,binding=deepcopy(base),receipt_sha256='0'*64)
    fragment=dict(fragment='launch-env-fragment-v5',environment='claude_code',profile=dict(name=profile,lock_sha256=lock),precedence=dict(winner='higher-weight',placement='winner-last'),env=dict(CLAUDE_CONFIG_DIR=manager+'/environments/'+profile+'/claude_code'),permissions=dict(mode='native',locked=False,source='default'),path_prepend=root,command_root=b)
    observed=dict(root_kind='directory',root_owner=owner,root_filesystem_id=rootmeta['filesystem_id'],root_object_id=rootmeta['object_id'],root_mode=0o700,files=files)
    if windows: observed['root_security_descriptor_sha256']=dacl
    s=dict(fragment=fragment,trusted=dict(profile=profile,names=[name],exports=[dict(skill='skill-one',name=name)],manager=manager,operator=owner,platform=platform,private_dacl=dacl,boundaries=[root,manager+'/interpreters']),observed=observed)
    seal(s,inventory,receipt,marker)
    return s


def edit_record(s,key,change):
    record=json.loads(s['trusted'][key]); change(record); seal(s,**{key:record})


def first_file(s):
    return next(iter(s['observed']['files'].values()))


def reference(s, settings=None):
    t=s['trusted']; windows=t['platform'].startswith('windows-')
    if settings is None: settings='C:/settings/hooks' if windows else '/settings/hooks'
    gateway=t['manager']+'/command-gateways/'+t['profile']+'/'+digest(settings)+'/bin/a2a'+('.cmd' if windows else '')
    gateway_bytes=('FIXTURE-GATEWAY-FORWARD/1\n'+gateway[:-4]+'.exe\n') if windows else 'dispatcher'
    r=dict(record='profile-command-reference/1',id=digest('reference'),profile=t['profile'],binding=deepcopy(t['binding']),command='a2a',owner=t['operator'],settings_resource=settings,gateway=gateway,gateway_sha256=digest(gateway_bytes),distribution_sha256=digest('signed distribution'),revision=1,phase='active')
    return dict(root=s,record=r,id_authority=r['id'],settings_authority=settings,distribution_authority=r['distribution_sha256'],gateway_bytes=gateway_bytes,revision_authority=1,externally_verified=True,signature_verified=True,caller=t['operator'],reference_count=1,root_count=1)


def session_pin(s):
    return dict(record='profile-command-session-pin/1',lease_id=digest('lease'),request_id=digest('request'),
                profile=s['trusted']['profile'],binding=deepcopy(s['trusted']['binding']),
                supervisor_instance=digest('supervisor'),boot_id='boot-one',process_domain='domain-one',
                process_started_at='start-one',revision=1,phase='active')


def launcher(s):
    prior=json.loads((ROOT/'conformance/profile-command-path/launcher-state.json').read_text())
    b=s['trusted']['binding']; t=s['trusted']; windows=t['platform'].startswith('windows-')
    prior['binding'].update(profile=t['profile'],lock_sha256='sha256:'+b['lock_sha256'],plan_sha256='sha256:'+b['plan_sha256'])
    tools=['C:/tools'] if windows else ['/tools']; base=['C:/base'] if windows else ['/usr/bin']
    effective=tools+[s['fragment']['path_prepend']]+base
    r=dict(record='launcher-path-state/2',prior_state=prior,command_root=deepcopy(b),lease_id=digest('lease'),effective_path=effective,path_value=(';' if windows else ':').join(effective))
    return dict(root=s,record=r,session_pin=session_pin(s),lease_authority=digest('lease'),pin_authority=deepcopy(session_pin(s)),protected_tools=tools,base_path=base)


def retention(s):
    roots=[dict(profile=s['trusted']['profile'],binding=deepcopy(s['trusted']['binding']))]; refs=[digest('reference')]
    r=dict(record='profile-command-roots/1',descriptor_sha256=digest('descriptor'),roots=deepcopy(roots),references=list(refs))
    return dict(record=r,descriptor='descriptor',roots_authority=roots,references_authority=refs,available_roots=deepcopy(roots),available_references=list(refs))


def output():
    base=fixture(); data=dict(version='profile-command-roots-v1',cases=[],references=[],launchers=[],retention=[],sessions=[],hooks=[],lifecycle=[],compatibility=[],transactions=[],two_profiles=[fixture('first','one'),fixture('second','two')],hook_upgrade=[fixture('work','one'),fixture('work','two')])
    def add(section,label,state,reason='verified',change=None):
        state=deepcopy(state)
        if change: change(state)
        codes = {'reference-cap':'profile_command_reference_limit',
                 'retention-cap':'profile_command_reference_limit',
                 'reference-owner':'profile_command_reference_authority',
                 'reference-id':'profile_command_reference_conflict',
                 'reference-settings':'profile_command_reference_conflict',
                 'reference-revision':'profile_command_reference_conflict',
                 'session-request':'profile_command_reference_conflict',
                 'session-unconfirmed':'profile_command_reference_unconfirmed',
                 'session-break-unconfirmed':'profile_command_reference_unconfirmed'}
        data[section].append(dict(id=label,state=state,expected=('accept' if reason=='verified' else codes.get(reason, 'profile_command_root_invalid')),reason=reason))
    def case(label,reason,change=None,state=base): add('cases',label,state,reason,change)
    case('valid-root','verified'); case('valid-windows','verified',state=fixture(platform='windows-amd64')); case('valid-script','verified',state=fixture(script=True))
    case('realistic-shape','verified',state=fixture(manager='/'+('m'*17),profile='p'*23))
    case('profile-64','verified',state=fixture(manager='/'+('m'*17),profile='p'*64))
    case('profile-64-windows','verified',state=fixture(manager='C:/'+('m'*15),profile='p'*64,platform='windows-amd64'))
    # Adjacent longest declared paths: the receipt is longer than this export.
    for length,reason in [(240,'verified'),(241,'path-limit')]:
        exemplar=fixture()
        receipt=exemplar['fragment']['path_prepend']+'/.curator-profile-command-root.json'
        manager='/'+('m'*(length-len(receipt)+1))
        case('path-'+str(length),reason,state=fixture(manager=manager))
    case('tampered-root','file-digest',lambda s:first_file(s).update(bytes='changed!!!',size=10))
    case('missing-root','root-kind',lambda s:s['observed'].update(root_kind='missing'))
    for key in ['marker','receipt','inventory']:
        # Valid JSON changed only in observed bytes, not a parse-error refusal.
        case('tampered-'+key,key+'-pin',lambda s,k=key:s['observed'].update({k:canonical(json.loads(s['observed'][k]))+' '}))
    case('missing-marker','marker-pin',lambda s:s['observed'].update(marker=None))
    case('tampered-pin','fragment-binding',lambda s:s['fragment']['profile'].update(lock_sha256='f'*64))
    case('missing-pin','fragment-schema',lambda s:s['fragment']['profile'].pop('lock_sha256'))
    case('inventory-pin','fragment-binding',lambda s:s['fragment']['command_root'].update(inventory_sha256='f'*64))
    case('older-fragment','fragment-schema',lambda s:s['fragment'].update(fragment='launch-env-fragment-v4'))
    case('linked-artifact','file-kind',lambda s:first_file(s).update(kind='symlink'))
    case('hardlinked-artifact','file-kind',lambda s:first_file(s).update(links=2))
    case('unsafe-mode','root-protection',lambda s:s['observed'].update(root_mode=0o777))
    case('readable-root','root-protection',lambda s:s['observed'].update(root_mode=0o755))
    case('root-object-substitution','root-object',lambda s:s['observed'].update(root_object_id='other'))
    case('file-object-substitution','file-object',lambda s:first_file(s).update(object_id='other'))
    case('wrong-owner','root-owner',lambda s:s['observed'].update(root_owner='uid:2000'))
    case('platform-substitution','platform',lambda s:s['trusted'].update(platform='darwin-arm64'))
    case('reserved-name','export-names',state=fixture(name='curator-evil'))
    case('device-name','export-names',state=fixture(name='con'))
    case('empty-exports','export-names',lambda s:s['trusted'].update(names=[]))
    case('colliding-skills','collision',lambda s:s['trusted']['exports'].append(dict(skill='skill-two',name='a2a')))
    case('foreign-root','root-path',lambda s:s['fragment'].update(path_prepend='/foreign/bin'))
    case('missing-receipt','receipt-pin',lambda s:s['observed'].update(receipt=None))
    case('unlisted-helper','file-inventory',lambda s:s['observed']['files'].update({'/m/helper':deepcopy(first_file(s))}))
    case('unknown-fragment-field','fragment-schema',lambda s:s['fragment'].update(extra=True))
    case('path-overflow','path-limit',state=fixture(manager='/'+('a'*180)))
    # Marker fits; the declared 63-byte command exceeds 240.
    case('command-path-overflow','path-limit',state=fixture(manager='/'+('a'*75),name='a'*63))
    case('windows-path-list','fragment-schema',lambda s:s['fragment'].update(path_prepend='C:/a;D:/b'),fixture(platform='windows-amd64'))
    case('windows-alternate-stream','fragment-schema',lambda s:s['fragment'].update(path_prepend='C:/a:stream'),fixture(platform='windows-amd64'))
    case('profile-device','profile-device',state=fixture(profile='con'))
    case('profile-grammar','profile-grammar',state=fixture(profile='a'*65))
    case('marker-binding','marker-binding',lambda s:edit_record(s,'marker',lambda r:r.update(profile='foreign')))
    case('receipt-binding','receipt-binding',lambda s:edit_record(s,'receipt',lambda r:r.update(profile='foreign')))
    for key in ['inventory','marker','receipt']:
        case(key+'-schema',key+'-schema',lambda s,k=key:edit_record(s,k,lambda r:r.update(unknown=True)))
    case('receipt-command','receipt-commands',lambda s:edit_record(s,'receipt',lambda r:r['commands'].append(deepcopy(r['commands'][0]))))
    case('inventory-command','inventory-commands',lambda s:edit_record(s,'inventory',lambda r:r['commands'].append(deepcopy(r['commands'][0]))))
    case('wrong-chain','chain-entry',lambda s:change_chain_path(s))
    case('script-target','chain-target',lambda s:edit_record(s,'inventory',lambda r:r['commands'][0]['chain'][0].update(target='/other')),fixture(script=True))
    case('script-digest','file-digest',lambda s:first_file(s).update(bytes='X'*first_file(s)['size']),fixture(script=True))
    case('script-cycle','chain-cycle',lambda s:edit_record(s,'inventory',lambda r:r['commands'][0]['chain'].append(deepcopy(r['commands'][0]['chain'][0]))),fixture(script=True))
    case('windows-cmd-target','chain-target',lambda s:edit_record(s,'inventory',lambda r:r['commands'][0]['chain'][0].update(target='C:/wrong.exe')),fixture(platform='windows-amd64'))
    case('windows-extra-suffix','file-inventory',lambda s:s['observed']['files'].update({'C:/m/a2a.bat':deepcopy(first_file(s))}),fixture(platform='windows-amd64'))
    case('native-cap','native-cap',lambda s:first_file(s).update(size=1024**3+1))
    case('script-cap','script-cap',lambda s:first_file(s).update(size=64*1024**2+1),fixture(script=True))
    case('file-cap','file-cap',state=many_files())
    case('metadata-cap','metadata-cap',lambda s:s['trusted'].update(marker=' '*(1024**2+1)))
    case('metadata-pin','marker-pin',lambda s:s['trusted'].update(marker=s['trusted']['marker']+' '))
    case('chain-depth','inventory-schema',lambda s:edit_record(s,'inventory',lambda r:r['commands'][0].update(chain=r['commands'][0]['chain']*9)))
    case('file-mode','file-protection',lambda s:first_file(s).update(mode=0o700))
    case('file-owner','file-owner',lambda s:first_file(s).update(owner='uid:2000'))
    case('malformed-metadata','metadata-json',state=bad_metadata('{'))
    case('duplicate-metadata','metadata-json',state=bad_metadata('{"record":1,"record":2}'))
    case('plan-union','plan-union',lambda s:s['trusted']['exports'][0].update(name='other'))
    case('file-size','file-size',lambda s:first_file(s).update(size=100))
    case('chain-kind','chain-kind',lambda s:edit_record(s,'inventory',lambda r:r['commands'][0]['chain'][0].update(kind='forwarder')))
    case('forwarder-bytes','forwarder-bytes',state=wrong_forwarder())
    case('executable-pin','executable-pin',lambda s:edit_record(s,'receipt',lambda r:r['commands'][0].update(executable_sha256='f'*64)))
    case('chain-confinement','chain-confinement',state=escaped_interpreter())
    case('root-dacl','root-protection',lambda s:s['observed'].update(root_security_descriptor_sha256='sha256:'+'f'*64),fixture(platform='windows-amd64'))
    case('windows-file-dacl','file-protection',lambda s:first_file(s).update(security_descriptor_sha256='sha256:'+'f'*64),fixture(platform='windows-amd64'))
    hook=dict(root=two_commands(),command='a2a')
    add('hooks','hook-selected-valid',hook)
    add('hooks','hook-unrelated-tamper',hook,change=lambda c:c['root']['observed']['files'][c['root']['fragment']['path_prepend']+'/other'].update(bytes='X'*10))
    add('hooks','hook-selected-tamper',hook,'file-digest',lambda c:first_file(c['root']).update(bytes='X'*10))
    add('hooks','hook-metadata-tamper',hook,'marker-pin',lambda c:c['root']['observed'].update(marker=c['root']['observed']['marker']+' '))
    add('hooks','hook-command-missing',hook,'hook-command',lambda c:c.update(command='missing'))
    pin=session_pin(base)
    session=dict(record=pin,pin_authority=deepcopy(pin),profile_authority=base['trusted']['profile'],binding_authority=deepcopy(base['trusted']['binding']),request_authority=pin['request_id'],incarnation_authority=['boot-one','domain-one','start-one'],operation='observe',observer_confirmed=True,descendants_quiescent=True,operator=False,fenced=False,revision=1,reason='',audit_durable=False)
    add('sessions','session-active',session)
    add('sessions','session-unknown',session,change=lambda c:(c['record'].update(phase='unknown'),c['pin_authority'].update(phase='unknown')))
    add('sessions','session-phase',session,'session-phase',lambda c:c['record'].update(phase='released'))
    add('sessions','session-release',session,change=lambda c:c.update(operation='release'))
    add('sessions','session-dead-pid',session,'session-unconfirmed',lambda c:c.update(operation='release',observer_confirmed=False))
    add('sessions','session-descendant',session,'session-unconfirmed',lambda c:c.update(operation='release',descendants_quiescent=False))
    add('sessions','session-break',session,change=lambda c:c.update(operation='break',operator=True,fenced=True,reason='domain fenced',audit_durable=True))
    add('sessions','session-break-unfenced',session,'session-break-unconfirmed',lambda c:c.update(operation='break',operator=True,fenced=False,reason='unknown domain',audit_durable=True))
    add('sessions','session-schema',session,'session-schema',lambda c:c['record'].update(extra=True))
    add('sessions','session-incarnation',session,'session-incarnation',lambda c:c['record'].update(boot_id='other'))
    add('sessions','session-profile',session,'session-binding',lambda c:c['record'].update(profile='foreign'))
    add('sessions','session-generation',session,'session-binding',lambda c:c['record']['binding'].update(generation='f'*64))
    add('sessions','session-discriminator',session,'session-schema',lambda c:c['record'].pop('record'))
    add('sessions','session-request',session,'session-request',lambda c:c['record'].update(request_id='f'*64))
    for field, label in [('lease_id','lease'), ('supervisor_instance','supervisor'),
                         ('revision','revision'), ('process_domain','domain'),
                         ('process_started_at','start')]:
        value = 2 if field == 'revision' else digest('other')
        add('sessions','session-'+label,session,('session-incarnation' if label in ['domain','start'] else 'session-'+label),
            lambda c,f=field,v=value:c['record'].update({f:v}))
    add('sessions','session-next-revision',session,change=lambda c:(
        c['record'].update(revision=2),c['pin_authority'].update(revision=2)))
    for section,seed in [('references',reference(base)),('launchers',launcher(base)),('retention',retention(base))]:
        prefix={'references':'reference','launchers':'launcher','retention':'retention'}[section]
        add(section,prefix+'-valid',seed)
    ref=reference(base)
    add('references','reference-second-resource',reference(base, '/projects/second/.codex/hooks.json'))
    add('references','reference-windows',reference(fixture(platform='windows-amd64')))
    for label,reason,change in [
        ('gateway','reference-gateway',lambda c:c['record'].update(gateway='/usr/local/bin/a2a')),
        ('id','reference-id',lambda c:c['record'].update(id='f'*64)),
        ('command','reference-command',lambda c:c['record'].update(command='other')),
        ('unexported','reference-command',lambda c:c['record'].update(command='helper')),
        ('binding','reference-binding',lambda c:c['record']['binding'].update(generation='f'*64)),
        ('owner','reference-owner',lambda c:c['record'].update(owner='uid:2000')),
        ('settings','reference-settings',lambda c:c['record'].update(settings_resource='/other')),
        ('distribution','reference-distribution',lambda c:c['record'].update(distribution_sha256='f'*64)),
        ('digest','reference-digest',lambda c:c['record'].update(gateway_sha256='f'*64)),
        ('revision','reference-revision',lambda c:c['record'].update(revision=2)),
        ('cap','reference-cap',lambda c:c.update(reference_count=257)),
        ('root-cap','reference-cap',lambda c:c.update(root_count=257)),
        ('unknown','reference-schema',lambda c:c['record'].update(extra=True)),
        ('external','reference-external',lambda c:c.update(externally_verified=False)),
        ('signature','reference-signature',lambda c:c.update(signature_verified=False))]:
        add('references','reference-'+label,ref,reason,change)
    launch=launcher(base)
    add('launchers','launcher-windows',launcher(fixture(platform='windows-amd64')))
    for label,reason,change in [
        ('schema','launcher-schema',lambda c:c['record'].update(extra=True)),
        ('session-schema','launcher-session-schema',lambda c:c['session_pin'].pop('record')),
        ('session-generation','launcher-lease',lambda c:c['session_pin']['binding'].update(generation='f'*64)),
        ('session-profile','launcher-lease',lambda c:c['session_pin'].update(profile='foreign')),
        ('session-id','launcher-lease',lambda c:c['session_pin'].update(lease_id='f'*64)),
        ('session-phase','launcher-lease',lambda c:c['session_pin'].update(phase='released')),
        ('ambient-first','launcher-order',lambda c:c['record']['effective_path'].reverse()),
        ('root-absent','launcher-order',lambda c:c['record']['effective_path'].pop(1)),
        ('path-value','launcher-path-value',lambda c:c['record'].update(path_value='/ambient')),
        ('binding','launcher-binding',lambda c:c['record']['command_root'].update(generation='f'*64)),
        ('prior','launcher-prior',lambda c:c['record']['prior_state']['binding'].update(profile='foreign')),
        ('lease','launcher-lease',lambda c:c['record'].update(lease_id='f'*64))]:
        add('launchers','launcher-'+label,launch,reason,change)
    for field, label in [('revision','revision'), ('supervisor_instance','supervisor'),
                         ('boot_id','boot'), ('process_domain','domain'),
                         ('process_started_at','start'), ('request_id','request')]:
        value = 2 if field == 'revision' else digest('other')
        add('launchers','launcher-session-'+label,launch,'launcher-session-'+label,
            lambda c,f=field,v=value:c['session_pin'].update({f:v}))
    add('launchers','launcher-next-revision',launch,change=lambda c:(
        c['session_pin'].update(revision=2),c['pin_authority'].update(revision=2)))
    add('launchers','launcher-authority-unknown',launch,'launcher-session-phase',lambda c:c['pin_authority'].update(phase='unknown'))
    ret=retention(base)
    for label,reason,change in [
        ('missing','retention-missing',lambda c:c.update(available_roots=[])),
        ('descriptor','retention-descriptor',lambda c:c['record'].update(descriptor_sha256='f'*64)),
        ('reference','retention-references',lambda c:c['record'].update(references=[])),
        ('binding','retention-roots',lambda c:c['record']['roots'][0]['binding'].update(generation='f'*64)),
        ('cap','retention-cap',lambda c:c['record'].update(roots=c['record']['roots']*257)),
        ('unknown','retention-schema',lambda c:c['record'].update(extra=True))]:
        add('retention','retention-'+label,ret,reason,change)
    def transition(section,label,state,expected): data[section].append(dict(id=label,state=state,expected=expected))
    empty={k:False for k in ['reference','session','snapshot','rollback','journal','descendant','unknown','installed','missing']}; empty['operation']='gc'
    for label,key,expected in [('retained-hook','reference','accept'),('session-live','session','retain'),('snapshot-live','snapshot','retain'),('rollback-live','rollback','retain'),('journal-live','journal','retain'),('descendant-live','descendant','retain'),('unknown-live','unknown','retain'),('installed-live','installed','retain')]:
        transition('lifecycle',label,dict(empty,**{key:True}),expected)
    transition('lifecycle','permitted-gc',dict(empty),'collect')
    transition('lifecycle','missing-root-hook',dict(empty,reference=True,missing=True),'profile_command_root_invalid')
    transition('lifecycle','purge-live',dict(empty,operation='purge',journal=True),'profile_command_root_in_use')
    transition('lifecycle','purge-empty',dict(empty,operation='purge'),'collect')
    for label,m,l,c,fence,fragment,expected in [
        ('new-new',True,True,True,True,5,'verify-v5'),('new-old',True,False,True,True,5,'reject-v5'),
        ('old-new',False,True,True,True,4,'refuse-before-resolve'),('old-old',False,False,True,True,4,'refuse-before-resolve'),
        ('no-commands',False,True,False,True,4,'legacy-no-prepend'),('legacy-v4',True,True,True,True,4,'refuse-before-start'),
        ('unfenced-activation',True,True,True,False,5,'refuse-before-resolve')]:
        transition('compatibility',label,dict(manager_new=m,launcher_new=l,commands=c,fenced=fence,fragment=fragment),expected)
    for label,op,valid,inputs,expected in [
        ('repair-tampered-launch','resolve-repair',False,True,'refuse-unchanged'),('repair-valid-launch','resolve-repair',True,True,'unchanged'),
        ('repair-explicit','explicit-repair',False,True,'fresh-generation-preserve-old'),('repair-pinned-restore','explicit-repair',False,True,'fresh-generation-preserve-old'),
        ('repair-stale-session','explicit-repair',False,True,'refuse-unchanged'),
        ('repair-stale-reconciled','explicit-repair',False,True,'fresh-generation-preserve-old'),
        ('repair-stale-broken','explicit-repair',False,True,'fresh-generation-preserve-old'),
        ('repair-stale-unfenced','explicit-repair',False,True,'refuse-unchanged'),
        ('repair-stale-unaudited','explicit-repair',False,True,'refuse-unchanged'),
        ('repair-stale-revision','explicit-repair',False,True,'refuse-unchanged'),
        ('repair-stale-descendant','explicit-repair',False,True,'refuse-unchanged'),
        ('repair-retargeted','explicit-repair',False,True,'refuse-unchanged'),
        ('repair-live-dropped','explicit-repair',False,True,'refuse-unchanged'),
        ('repair-inputs-differ','explicit-repair',False,True,'refuse-unchanged'),('repair-generation-reused','explicit-repair',False,True,'refuse-unchanged'),('repair-input-missing','explicit-repair',False,False,'refuse-unchanged'),
        ('update-refused','refused-update',False,True,'all-preimages-old')]:
        transition('transactions',label,dict(operation=op,valid=valid,inputs=inputs),expected)
    for phase,expected in [('preparing','all-preimages-old'),('prepared','complete-new'),('committing','complete-new'),('cleanup','complete-new'),('rolling_back','all-preimages-old'),('rollback_cleanup','all-preimages-old'),('unknown','refuse-preserve-journal')]:
        transition('transactions','journal-'+phase.replace('_','-'),dict(operation='recover',phase=phase),expected)
    # Exact old/new observation sets are literals owned by the generator;
    # the independent transaction model must reconstruct the selected set.
    old={k:digest('old '+k) for k in ['lock','source','plan','executable','build_receipt','root','marker','receipt','inventory','pointer','prompt','unrelated']}
    for case in data['transactions']:
        state=case['state']; outcome=case['expected']; staged={k:digest('new '+k) for k in old}
        if state['operation']=='explicit-repair':
            for key in ['lock','source','plan','executable','build_receipt','unrelated']: staged[key]=old[key]
        staged['unrelated']=old['unrelated']
        state.update(before=deepcopy(old),staged=staged,old_generation=digest('old generation'),new_generation=digest('new generation'))
        if case['id']=='repair-inputs-differ': staged['source']=digest('different source')
        if case['id']=='repair-generation-reused': state['new_generation']=state['old_generation']
        edge=dict(kind='none',generation=state['old_generation'],revision=1)
        label=case['id']
        if label in ['repair-pinned-restore','repair-retargeted','repair-live-dropped']: edge['kind']='live-session'
        if label.startswith('repair-stale-'): edge['kind']='unknown-session'
        state.update(retained_edge=edge,staged_edge=deepcopy(edge),observer_confirmed=False,
                     descendants_quiescent=False,operator=False,fenced=False,audit_durable=False,
                     reason='',if_revision=1)
        if label in ['repair-stale-reconciled','repair-stale-descendant']: state.update(observer_confirmed=True,descendants_quiescent=label=='repair-stale-reconciled')
        if label in ['repair-stale-broken','repair-stale-unfenced','repair-stale-unaudited','repair-stale-revision']:
            state.update(operator=True,fenced=label!='repair-stale-unfenced',audit_durable=label!='repair-stale-unaudited',reason='domain fenced')
        if label=='repair-stale-revision': state['if_revision']=2
        if label=='repair-retargeted': state['staged_edge']['generation']=state['new_generation']
        if label=='repair-live-dropped': state['staged_edge']['kind']='none'
        publish=outcome in ['complete-new','fresh-generation-preserve-old']
        case['expected']=dict(refusal=({'repair-stale-session':'repair-session-unconfirmed','repair-stale-unfenced':'repair-session-unconfirmed','repair-retargeted':'repair-edge-changed','repair-live-dropped':'repair-edge-changed'}.get(label,'repair-session-unconfirmed' if label.startswith('repair-stale-') else 'repair-inputs-or-generation') if state['operation']=='explicit-repair' and outcome=='refuse-unchanged' else ''),retained_edge=deepcopy(edge),outcome=outcome,live=deepcopy(staged if publish else old),preserved_old=deepcopy(old),pending_journal=outcome=='refuse-preserve-journal',evidence_generations=([state['old_generation'],state['new_generation']] if publish or outcome=='refuse-preserve-journal' else [state['old_generation']]))
    return data


def two_commands():
    s=fixture(); inv=json.loads(s['trusted']['inventory']); receipt=json.loads(s['trusted']['receipt'])
    root=s['fragment']['path_prepend']; other=deepcopy(inv['commands'][0]); other['name']='other'
    other['chain'][0]['path']=root+'/other'; other['chain'][0]['metadata']['object_id']=digest('other object')
    inv['commands'].append(other)
    command=deepcopy(receipt['commands'][0]); command['name']='other'; receipt['commands'].append(command)
    s['observed']['files'][root+'/other']=deepcopy(first_file(s)); s['observed']['files'][root+'/other']['object_id']=digest('other object')
    s['trusted']['names'].append('other'); s['trusted']['exports'].append(dict(name='other',skill='skill-two'))
    seal(s,inventory=inv,receipt=receipt)
    return s


def bad_metadata(content):
    s=fixture(); b=s['fragment']['command_root']
    s['trusted']['marker']=s['observed']['marker']=content
    b['marker_sha256']=digest(content); s['trusted']['binding']=deepcopy(b)
    return s


def wrong_forwarder():
    s=fixture(script=True); a=first_file(s); a['bytes']='X'*a['size']
    edit_record(s,'inventory',lambda r:r['commands'][0]['chain'][0].update(sha256='sha256:'+digest(a['bytes'])))
    return s


def escaped_interpreter():
    s=fixture(script=True); inv=json.loads(s['trusted']['inventory']); chain=inv['commands'][0]['chain']
    old=chain[1]['path']; new='/outside/interpreter'
    s['observed']['files'][new]=s['observed']['files'].pop(old)
    chain[1]['path']=new; chain[0]['target']=new
    a=first_file(s); a['bytes']='FIXTURE-FORWARD/1\n'+new+'\n'; a['size']=len(a['bytes'])
    chain[0]['sha256']='sha256:'+digest(a['bytes']); seal(s,inventory=inv)
    return s


def many_files():
    s=fixture(); inv=json.loads(s['trusted']['inventory']); rec=json.loads(s['trusted']['receipt'])
    root=s['fragment']['path_prepend']; exemplar=deepcopy(first_file(s)); meta=inv['commands'][0]['chain'][0]['metadata']
    inv['commands']=[]; rec['commands']*=129; s['observed']['files']={}
    names=[f'cmd-{i:03}' for i in range(129)]
    for i,name in enumerate(names):
        rec['commands'][i]=deepcopy(rec['commands'][i]); rec['commands'][i]['name']=name
        chain=[]
        for j in range(8):
            path=root+'/'+name+('' if j==0 else f'-hop-{j}')
            terminal=j==7
            target=None if terminal else root+'/'+name+f'-hop-{j+1}'
            content=exemplar['bytes'] if terminal else 'FIXTURE-FORWARD/1\n'+target+'\n'
            hopmeta=deepcopy(meta); hopmeta['object_id']=digest(path)
            s['observed']['files'][path]=dict(deepcopy(exemplar),bytes=content,size=len(content),format='native' if terminal else 'forwarder',object_id=hopmeta['object_id'])
            chain.append(dict(path=path,kind='executable' if terminal else 'forwarder',metadata=hopmeta,sha256='sha256:'+digest(content),target=target))
        inv['commands'].append(dict(name=name,chain=chain))
    s['trusted']['names']=names; s['trusted']['exports']=[dict(name=n,skill='skill-one') for n in names]
    seal(s,inventory=inv,receipt=rec)
    return s


def change_chain_path(s):
    old=next(iter(s['observed']['files'])); new=old+'-other'
    s['observed']['files'][new]=s['observed']['files'].pop(old)
    edit_record(s,'inventory',lambda r:r['commands'][0]['chain'][0].update(path=new))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--check',action='store_true'); args=parser.parse_args()
    path=ROOT/'conformance/profile-command-roots-v1/cases.json'; data=json.dumps(output(),indent=2)+'\n'
    if args.check:
        if not path.exists() or path.read_text()!=data: raise SystemExit('command-root regeneration differs')
    else: path.write_text(data)


if __name__=='__main__': main()
