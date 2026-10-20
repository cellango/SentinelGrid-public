"""Compile/run only the exact owned JDK sentinel with processing disabled."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import types

if not __debug__:
    raise RuntimeError("Optimized Python unsupported; validation must remain enabled")
FIXTURE = Path(__file__).resolve().parent
root = Path(sys.argv[1]).resolve()
state = json.loads((root / "state.json").read_text())
inputs = json.loads((FIXTURE / "inputs.json").read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert all(sha(FIXTURE / name) == value for name, value in inputs["fixture_sha256"].items())
module = types.ModuleType("trusted_jvm_prepare")
module.__file__ = str(FIXTURE / "prepare.py")
exec(compile((FIXTURE / "prepare.py").read_bytes(), str(FIXTURE / "prepare.py"), "exec"), module.__dict__)
_, java, java_home = module.validate(Path(state["tool_root"]))
assert state["root"] == str(root) and state["java"] == str(java) and state["java_home"] == str(java_home)
assert os.stat(root).st_uid == os.getuid() and os.stat(root).st_mode & 0o077 == 0
work = root / "work"
profile = root / "default-deny.sb"
assert profile.read_text() == module.profile_text(java, java_home, root)
assert sha(profile) == state["profile_sha256"]
assert sha(work / "JvmBoundaryProbe.java") == inputs["fixture_sha256"]["JvmBoundaryProbe.java"]
assert not list((work / "classes").iterdir()) and not list((work / "empty").iterdir())
canary = root / "denied-canary.txt"
assert not canary.is_symlink() and canary.stat().st_nlink == 1
assert (work / "escape-link").is_symlink() and (work / "escape-link").resolve() == canary
environment = {"PATH": "/usr/bin:/bin", "TMPDIR": str(work / "tmp") + "/", "LC_ALL": "C", "HOME": str(work / "home")}
options = [str(java), "-Xint", "-Xms16m", "-Xmx64m", "-XX:ActiveProcessorCount=2", "-XX:-UsePerfData", "-XX:+DisableAttachMechanism", "-XX:-CreateCoredumpOnCrash", "-XX:ErrorFile=" + str(work / "hs_err_pid%p.log"), "-Duser.home=" + str(work / "home"), "-Djava.io.tmpdir=" + str(work / "tmp"), "-Duser.timezone=UTC"]
guard = ["/usr/bin/sandbox-exec", "-f", str(profile)]
def invoke(command, stdin=subprocess.DEVNULL):
    result = subprocess.run(command, cwd=work, env=environment, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25, close_fds=True, pass_fds=())
    return dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)

compile_command = guard + options + ["-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "21", "-proc:none", "-implicit:none", "-classpath", str(work / "empty"), "-sourcepath", str(work / "empty"), "-d", str(work / "classes"), str(work / "JvmBoundaryProbe.java")]
compilation = invoke(compile_command)
(root / "compile.json").write_text(json.dumps(compilation, indent=2) + "\n")
assert compilation["returncode"] == 0, compilation
classes = {str(path.relative_to(work / "classes")): sha(path) for path in (work / "classes").rglob("*") if path.is_file()}
assert set(classes) == {"JvmBoundaryProbe.class", "JvmBoundaryProbe$Operation.class"}
tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp.bind(("127.0.0.1", 0))
port = tcp.getsockname()[1]
unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
unix_path = root / "owned-ipc.sock"
unix.bind(str(unix_path))
rows = []
try:
    for mode, guarded, inherited in [("unguarded_baseline", False, False), ("guarded_closed_fds", True, False), ("guarded_inherited_stdin_negative", True, True)]:
        for path in [work / "hardlink-escape", Path(str(canary) + ".write")]:
            if path.exists():
                path.unlink()
        assert canary.stat().st_nlink == 1
        command = (guard if guarded else []) + options + ["--limit-modules=java.base", "-cp", str(work / "classes"), "JvmBoundaryProbe", str(work), str(canary), str(port), str(unix_path)]
        before = sha(canary)
        if inherited:
            with canary.open("rb") as stream:
                result = invoke(command, stream)  # Intentional owned read capability in FD0; not the secure launcher.
        else:
            result = invoke(command)
        result.update(mode=mode, guarded=guarded, intentionally_inherited_owned_stdin=inherited, canary_changed=sha(canary) != before)
        try:
            result["observations"] = [json.loads(line) for line in result["stdout"].splitlines()]
        except Exception:
            result["observations"] = None
        rows.append(result)
finally:
    tcp.close()
    unix.close()
    unix_path.unlink(missing_ok=True)
    record = dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), compilation=compilation, class_sha256=classes, rows=rows, native_and_Java_home_owned=True, no_dynamic_code_permission_added=True, only_JDK_compiler_proc_none_and_trusted_owned_probe=True, no_Maven_modelresolver_plugin_Quarkus_issuer_provider_or_A0_candidate=True, full_effect_disabled_harness_qualified=False)
    (root / "results.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(dict(rows=[dict(mode=row["mode"],returncode=row["returncode"],observations=row["observations"]) for row in rows],full_harness_qualified=False)))
assert len(rows) == 3 and all(row["returncode"] == 0 and row["observations"] is not None and len(row["observations"]) == 17 for row in rows)
observations = {row["mode"]: {probe["name"]: probe for probe in row["observations"]} for row in rows}
denials = ["outside_owned_canary_read", "outside_owned_canary_stat", "outside_owned_canary_write", "symlink_escape_read", "hardlink_escape_create", "loopback_owned_bound_port_connect", "loopback_socket_bind_no_listen", "owned_unix_socket_connect", "thread_outside_canary_read", "thread_loopback_socket_bind_no_listen"]
positive = ["owned_home_and_environment", "owned_work_write", "owned_work_read", "thread_owned_work_write"]
for mode in ["guarded_closed_fds", "guarded_inherited_stdin_negative"]:
    current = observations[mode]
    assert all(current[name]["outcome"] == "allowed" for name in positive)
    assert all(current[name]["outcome"] == "denied_or_failed" and ("Operation not permitted" in current[name]["message"] or "error=1" in current[name]["message"]) for name in denials)
# macOS JDK reports generic spawn-helper failure here, not a reliable kernel errno.
# Require the actual failure and retain the diagnostic; do not label it EPERM proof.
for mode in ["guarded_closed_fds", "guarded_inherited_stdin_negative"]:
    probe = observations[mode]["unapproved_OS_child_exec"]
    assert probe["outcome"] == "denied_or_failed" and probe["error_type"] == "java.io.IOException" and "posix_spawn failed" in probe["message"]
for mode in ["guarded_closed_fds", "guarded_inherited_stdin_negative"]:
    local = observations[mode]["localhost_name_resolution_only"]
    assert local["outcome"] == "allowed" and local["value"] == "[localhost/127.0.0.1]"
assert observations["guarded_closed_fds"]["inherited_stdin_canary_read"]["value"] == "-1"
assert observations["guarded_inherited_stdin_negative"]["inherited_stdin_canary_read"]["value"] == "83"
baseline = observations["unguarded_baseline"]
assert all(baseline[name]["outcome"] == "allowed" for name in positive + ["outside_owned_canary_read", "outside_owned_canary_stat", "outside_owned_canary_write", "symlink_escape_read", "hardlink_escape_create", "loopback_socket_bind_no_listen", "thread_outside_canary_read", "thread_loopback_socket_bind_no_listen", "localhost_name_resolution_only"])
assert baseline["inherited_stdin_canary_read"]["value"] == "-1"
assert baseline["loopback_owned_bound_port_connect"]["error_type"] in ["java.net.SocketTimeoutException", "java.net.ConnectException"]
assert baseline["owned_unix_socket_connect"]["error_type"] == "java.net.ConnectException" and "Connection refused" in baseline["owned_unix_socket_connect"]["message"]
assert all(not row["canary_changed"] for row in rows)
print(json.dumps(dict(expected_observations=51,closed_stdin_reads_EOF=True,inherited_stdin_canary_read_negative_witness=True,thread_file_and_socket_denials=True,complete_native_service_DNS_container_input_and_harness_qualification=False)))
