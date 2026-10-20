"""Owned harmless OS-resource probes. Never import issuer, Maven or provider code."""
import errno,json,os,socket,subprocess,sys
mode,work,canary,port,unix_path,inherited_fd=sys.argv[1:]
inherited_fd=int(inherited_fd);out=[]
def record(name,fn):
 try:result=fn();out.append(dict(name=name,outcome='allowed',value=result))
 except OSError as e:out.append(dict(name=name,outcome='denied_or_failed',errno=e.errno,error_type=type(e).__name__))
 except Exception as e:out.append(dict(name=name,outcome='unexpected_exception',error_type=type(e).__name__))
def read(p):
 with open(p) as f:return f.read(64)
def write(p):
 with open(p,'w') as f:f.write('OWNED_SENTINEL_ONLY')
 return True
def sock_connect(family,address):
 with socket.socket(family,socket.SOCK_STREAM) as s:s.settimeout(.5);s.connect(address)
 return True
def sock_bind():
 with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:s.bind(('127.0.0.1',0))
 return True
def fork_probe():
 pid=os.fork()
 if pid==0:os._exit(0)
 os.waitpid(pid,0);return True
def child_probe():
 r=subprocess.run(['/usr/bin/true'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=2,close_fds=True);return r.returncode
def inherited_probe():
 # Fixed high FD allocated by controller; this writes only its owned canary.
 os.write(inherited_fd,b'OWNED_INHERITED_FD_SENTINEL\n');return True
record('owned_work_write',lambda:write(work+'/inside.txt'))
record('owned_work_read',lambda:read(work+'/inside.txt'))
record('outside_owned_canary_read',lambda:read(canary))
record('outside_owned_canary_stat',lambda:os.stat(canary).st_size)
record('outside_owned_canary_write',lambda:write(canary+'.write'))
record('symlink_escape_read',lambda:read(work+'/escape-link'))
record('hardlink_escape_create',lambda:os.link(canary,work+'/hardlink-escape'))
record('loopback_owned_bound_port_connect',lambda:sock_connect(socket.AF_INET,('127.0.0.1',int(port))))
record('loopback_socket_bind_no_listen',sock_bind)
record('owned_unix_socket_connect',lambda:sock_connect(socket.AF_UNIX,unix_path))
record('localhost_name_resolution_only',lambda:[x[4][0] for x in socket.getaddrinfo('localhost',None)])
record('process_fork',fork_probe)
record('unapproved_OS_child_exec',child_probe)
record('inherited_canary_fd_write',inherited_probe)
print(json.dumps(dict(mode=mode,probe_rows=out,scope='trusted owned sentinel only;localhost resolution may be cached and is not external DNS traffic proof;connect ports/sockets belong to controller and never listen',no_native_JVM_Maven_provider_or_external_network_target=True)))
