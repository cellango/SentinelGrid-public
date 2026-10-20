"""Run only the reviewed offline model API, never Maven CLI or plugins."""
import hashlib,json,os
from pathlib import Path
import re,subprocess,sys,types
if not __debug__:
    raise RuntimeError("Optimized Python unsupported; validation must remain enabled")
FIXTURE=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
root=Path(sys.argv[1]).resolve();state=json.loads((root/'state.json').read_text());manifest=json.loads((FIXTURE/'inputs.json').read_text())
assert all(sha(FIXTURE/n)==h for n,h in manifest['fixture_sha256'].items())
m=types.ModuleType('trusted_offline_prepare');m.__file__=str(FIXTURE/'prepare.py');exec(compile((FIXTURE/'prepare.py').read_bytes(),str(FIXTURE/'prepare.py'),'exec'),m.__dict__)
_,java,java_home=m.validate(Path(state['tool_root']),Path(state['metadata_root']))
assert state['root']==str(root) and state['java']==str(java) and state['java_home']==str(java_home)
assert root.stat().st_uid==os.getuid() and root.stat().st_mode&0o077==0
profile=root/'default-deny.sb';work=root/'work';owned=root/'inputs'
assert profile.read_text()==m.profile_text(java,java_home,root) and sha(profile)==state['policy_sha256']
assert not owned.is_symlink() and all(not p.is_symlink() for p in owned.rglob('*'))
assert state['input_sha256']==m.expected_input_hashes(manifest)
assert set(state['input_sha256'])=={str(p.relative_to(root)) for p in owned.rglob('*') if p.is_file()}
assert all(not (root/n).is_symlink() and sha(root/n)==h for n,h in state['input_sha256'].items())
assert sha(work/'OfflineModelProbe.java')==manifest['fixture_sha256']['OfflineModelProbe.java']
assert not list((work/'classes').iterdir()) and not list((work/'empty').iterdir())
environment={'PATH':'/usr/bin:/bin','TMPDIR':str(work/'tmp')+'/', 'LC_ALL':'C','HOME':str(work/'home')}
options=[str(java),'-Xint','-Xshare:off','-Xms16m','-Xmx128m','-XX:ActiveProcessorCount=2','-XX:-UsePerfData','-XX:+DisableAttachMechanism','-XX:-CreateCoredumpOnCrash','-XX:ErrorFile='+str(work/'hs_err_pid%p.log'),'-Duser.home='+str(work/'home'),'-Djava.io.tmpdir='+str(work/'tmp'),'-Duser.timezone=UTC']
guard=['/usr/bin/sandbox-exec','-f',str(profile)]
libraries=[owned/'lib'/Path(x['path']).name for x in manifest['model_libraries']]
assert len(libraries)==6 and {str(p.relative_to(root)) for p in libraries}=={n for n in state['input_sha256'] if n.startswith('inputs/lib/')}
classpath=os.pathsep.join(str(p) for p in libraries)
def invoke(command):
 r=subprocess.run(command,cwd=work,env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=90,close_fds=True,pass_fds=())
 return dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
compile_command=guard+options+['-m','jdk.compiler/com.sun.tools.javac.Main','--release','21','-Xlint:deprecation','-proc:none','-implicit:none','-classpath',classpath,'-sourcepath',str(work/'empty'),'-d',str(work/'classes'),str(work/'OfflineModelProbe.java')]
compile_result=invoke(compile_command);(root/'compile.json').write_text(json.dumps(compile_result,indent=2)+'\n');assert compile_result['returncode']==0,compile_result
classes={str(p.relative_to(work/'classes')):sha(p) for p in (work/'classes').rglob('*') if p.is_file()}
command=guard+options+['--limit-modules=java.base,java.xml','-Xlog:class+load=info:file='+str(work/'loaded-classes.log'),'-cp',str(work/'classes')+os.pathsep+classpath,'OfflineModelProbe',str(owned),str(work),str(root/'outside-canary.txt')]
result=invoke(command)
try:result['observations']=[json.loads(line) for line in result['stdout'].splitlines()]
except Exception:result['observations']=None
origins=set(re.findall(r' source: (.*)',(work/'loaded-classes.log').read_text())) if (work/'loaded-classes.log').exists() else set()
record=dict(compilation=compile_result,execution=result,class_sha256=classes,classload_origins=sorted(origins),read_only_inputs_unchanged=all(sha(root/n)==h for n,h in state['input_sha256'].items()),native_build_plugin_processor_extension_issuer_or_provider=False,full_executable_artifact_provider_or_issuer_harness_qualified=False)
(root/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(returncode=result['returncode'],rows=result['observations'],classload_origins=sorted(origins),readonly_inputs_unchanged=record['read_only_inputs_unchanged'])))
assert result['returncode']==0 and result['observations'] is not None and record['read_only_inputs_unchanged']
# Hidden/lambda class origins name a verified defining class rather than a URL.
class_origins={}
for name,origin in re.findall(r'\[class,load\] (\S+) source: (.*)',(work/'loaded-classes.log').read_text()):
    class_origins.setdefault(name,set()).add(origin)
allowed_files={'file:'+str(p) for p in libraries}|{'file:'+str(work/'classes')+'/'}
def trusted(origin,seen=frozenset()):
    if origin.startswith('jrt:/') or origin in allowed_files or origin=='__JVM_LookupDefineClass__':return True
    if origin in seen or origin not in class_origins:return False
    return all(trusted(parent,seen|{origin}) for parent in class_origins[origin])
assert all(trusted(origin) for origin in origins),origins

summary=next(x for x in result['observations'] if x['name']=='summary');assert 'control_assertions=15;' in summary['detail']
native=[x for x in result['observations'] if x['name'].startswith('selected_native_model:')];assert len(native)==5
print(json.dumps(dict(bounded_model_controls=15,selected_native_model_successes=sum(x['outcome']=='model_only_success' for x in native),selected_native_model_NO_GO=sum(x['outcome']=='NO_GO' for x in native),full_native_graph_qualified=False)))
