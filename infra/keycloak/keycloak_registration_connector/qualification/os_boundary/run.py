from pathlib import Path
import datetime,fcntl,hashlib,json,os,socket,subprocess,sys,types
if not __debug__:
    raise RuntimeError('Optimized Python is unsupported: validation must stay enabled')
FIXTURE=Path(__file__).resolve().parent
O=Path(sys.argv[1]).resolve();r=json.loads((O/'state.json').read_text())
inputs=json.loads((FIXTURE/'inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(FIXTURE/n)==h for n,h in inputs['fixture_sha256'].items())
module=types.ModuleType('owned_boundary_prepare');module.__file__=str(FIXTURE/'prepare.py');exec(compile((FIXTURE/'prepare.py').read_bytes(),str(FIXTURE/'prepare.py'),'exec'),module.__dict__)
_,runtime,runtime_root=module.validate(Path(r['python_executable']))
root=Path(r['root']);work=Path(r['work']);canary=Path(r['canary']);profile=Path(r['profile'])
assert root==O and work==O/'work' and canary==O/'denied-canary.txt' and profile==O/'default-deny.sb' and Path(r['payload'])==O/'probe.py'
assert os.stat(O).st_uid==os.getuid() and os.stat(O).st_mode&0o077==0
assert profile.read_text()==module.profile_text(runtime,runtime_root,O)
assert all(sha(Path(p))==h for p,h in r['sha256s'].items())
assert canary.stat().st_nlink==1
env={'PATH':'/usr/bin:/bin','TMPDIR':str(root/'tmp')+'/', 'LC_ALL':'C'}
canary_fd=os.open(canary,os.O_WRONLY|os.O_APPEND);fd=fcntl.fcntl(canary_fd,fcntl.F_DUPFD_CLOEXEC,128);os.close(canary_fd)
tcp=socket.socket(socket.AF_INET,socket.SOCK_STREAM);tcp.bind(('127.0.0.1',0));port=tcp.getsockname()[1]
unix=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);unix_path=root/'owned-ipc.sock';unix.bind(str(unix_path))
rows=[]
try:
 for mode,guarded,inherit in [('unguarded_baseline',False,True),('guarded_closed_fds',True,False),('guarded_inherited_fd_negative',True,True)]:
  for path in [work/'hardlink-escape',Path(str(canary)+'.write')]:
   if path.exists():path.unlink()
  assert canary.stat().st_nlink==1
  command=[r['python_executable'],'-I','-S','-B',r['payload'],mode,str(work),str(canary),str(port),str(unix_path),str(fd)]
  if guarded:command=['/usr/bin/sandbox-exec','-f',str(profile),*command]
  before=sha(canary)
  result=subprocess.run(command,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15,close_fds=True,pass_fds=(fd,) if inherit else ())
  row=dict(mode=mode,guarded=guarded,deliberately_inherited_owned_canary_FD=inherit,command=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,canary_sha256_before=before,canary_sha256_after=sha(canary),canary_changed=sha(canary)!=before)
  try:row['observations']=json.loads(result.stdout)
  except Exception:row['observations']=None
  rows.append(row)
finally:
 os.close(fd);tcp.close();unix.close();unix_path.unlink(missing_ok=True)
 record=dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=rows,profile_sha256=sha(profile),trusted_OS_Python_owned_sentinel_scope_only=True,network_targets='only owned bound TCP/Unix sockets that NEVER listen;localhost name lookup only;no external target or real service',close_fds_required_before_profile_installation=True,no_JVM_Maven_plugin_processor_augmentation_native_build_or_test=True,complete_effect_disabled_harness_qualified=False)
 (O/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(results=[dict(mode=x['mode'],returncode=x['returncode'],rows=len(x['observations']['probe_rows']) if x['observations'] else 0,stderr=x['stderr'][:600]) for x in rows],scope='capability observations only;not full harness/admission proof')))

assert len(rows)==3 and all(x['returncode']==0 and x['observations'] is not None for x in rows)
observations={x['mode']:{p['name']:p for p in x['observations']['probe_rows']} for x in rows}
expected_denials=['outside_owned_canary_read','outside_owned_canary_stat','outside_owned_canary_write','symlink_escape_read','hardlink_escape_create','loopback_owned_bound_port_connect','loopback_socket_bind_no_listen','owned_unix_socket_connect','process_fork','unapproved_OS_child_exec']
for mode in ['guarded_closed_fds','guarded_inherited_fd_negative']:
    o=observations[mode]
    assert all(o[n]['outcome']=='allowed' for n in ['owned_work_write','owned_work_read'])
    assert all(o[n].get('errno')==1 and o[n]['error_type']=='PermissionError' for n in expected_denials)
    assert o['localhost_name_resolution_only']['error_type']=='gaierror'
assert observations['guarded_closed_fds']['inherited_canary_fd_write'].get('errno')==9
assert not next(x for x in rows if x['mode']=='guarded_closed_fds')['canary_changed']
assert observations['guarded_inherited_fd_negative']['inherited_canary_fd_write']['outcome']=='allowed'
assert next(x for x in rows if x['mode']=='guarded_inherited_fd_negative')['canary_changed']
baseline=observations['unguarded_baseline']
assert all(baseline[n]['outcome']=='allowed' for n in ['owned_work_write','owned_work_read','outside_owned_canary_read','outside_owned_canary_stat','outside_owned_canary_write','symlink_escape_read','hardlink_escape_create','loopback_socket_bind_no_listen','localhost_name_resolution_only','process_fork','unapproved_OS_child_exec','inherited_canary_fd_write'])
assert baseline['loopback_owned_bound_port_connect'].get('errno') not in [1,13]
assert baseline['owned_unix_socket_connect'].get('errno')==61
print(json.dumps(dict(expected_outcome_observations=42,closed_FD_canary_unchanged=True,inherited_FD_negative_witness_retained=True,bounded_owned_resource_denials_only=True,external_DNS_Mach_services_JVM_full_input_and_harness_qualification=False)))
