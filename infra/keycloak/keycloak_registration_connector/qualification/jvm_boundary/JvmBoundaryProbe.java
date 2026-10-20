import java.io.*;
import java.net.*;
import java.nio.channels.SocketChannel;
import java.nio.file.*;
import java.util.*;

/** Trusted owned sentinels only. No issuer, Maven, provider, JNI or real service. */
public final class JvmBoundaryProbe {
    interface Operation { Object call() throws Exception; }
    static String quote(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\"";
    }
    static synchronized void observe(String name, Operation operation) {
        try {
            Object result = operation.call();
            System.out.println("{\"name\":" + quote(name) + ",\"outcome\":\"allowed\",\"value\":" + quote(String.valueOf(result)) + "}");
        } catch (Exception error) {
            String message = String.valueOf(error.getMessage());
            if (message.length() > 400) message = message.substring(0, 400);
            System.out.println("{\"name\":" + quote(name) + ",\"outcome\":\"denied_or_failed\",\"error_type\":" + quote(error.getClass().getName()) + ",\"message\":" + quote(message) + "}");
        }
    }
    public static void main(String[] args) throws Exception {
        Path work = Path.of(args[0]), canary = Path.of(args[1]);
        int port = Integer.parseInt(args[2]);
        Path unix = Path.of(args[3]);
        observe("owned_home_and_environment", () -> {
            Set<String> keys = new TreeSet<>(System.getenv().keySet());
            if (!keys.containsAll(Set.of("HOME", "PATH", "TMPDIR", "LC_ALL")) || !Set.of("HOME", "PATH", "TMPDIR", "LC_ALL", "__CF_USER_TEXT_ENCODING").containsAll(keys)) throw new IllegalStateException("Unexpected child environment keys: " + keys);
            if (!System.getenv("HOME").equals(work.resolve("home").toString()) || !System.getProperty("user.home").equals(System.getenv("HOME"))) throw new IllegalStateException("Native/Java home mismatch");
            if (!System.getProperty("java.io.tmpdir").equals(work.resolve("tmp").toString())) throw new IllegalStateException("Temporary directory mismatch");
            return keys;
        });
        observe("owned_work_write", () -> Files.writeString(work.resolve("inside.txt"), "OWNED_JVM_SENTINEL"));
        observe("owned_work_read", () -> Files.readString(work.resolve("inside.txt")));
        observe("outside_owned_canary_read", () -> Files.readString(canary));
        observe("outside_owned_canary_stat", () -> Files.size(canary));
        observe("outside_owned_canary_write", () -> Files.writeString(Path.of(canary + ".write"), "OWNED_JVM_ONLY"));
        observe("symlink_escape_read", () -> Files.readString(work.resolve("escape-link")));
        observe("hardlink_escape_create", () -> Files.createLink(work.resolve("hardlink-escape"), canary));
        observe("loopback_owned_bound_port_connect", () -> {
            try (Socket socket = new Socket()) { socket.connect(new InetSocketAddress("127.0.0.1", port), 300); return true; }
        });
        observe("loopback_socket_bind_no_listen", () -> {
            try (Socket socket = new Socket()) { socket.bind(new InetSocketAddress("127.0.0.1", 0)); return true; }
        });
        observe("owned_unix_socket_connect", () -> {
            try (SocketChannel socket = SocketChannel.open(StandardProtocolFamily.UNIX)) { return socket.connect(UnixDomainSocketAddress.of(unix)); }
        });
        observe("localhost_name_resolution_only", () -> Arrays.toString(InetAddress.getAllByName("localhost")));
        observe("unapproved_OS_child_exec", () -> {
            Process child = new ProcessBuilder("/usr/bin/true").redirectInput(ProcessBuilder.Redirect.from(new File("/dev/null"))).start();
            if (!child.waitFor(2, java.util.concurrent.TimeUnit.SECONDS)) { child.destroyForcibly(); throw new IllegalStateException("Owned child timeout"); }
            return child.exitValue();
        });
        observe("inherited_stdin_canary_read", () -> System.in.read());
        Thread thread = new Thread(() -> {
            observe("thread_owned_work_write", () -> Files.writeString(work.resolve("thread.txt"), "OWNED_THREAD_ONLY"));
            observe("thread_outside_canary_read", () -> Files.readString(canary));
            observe("thread_loopback_socket_bind_no_listen", () -> {
                try (Socket socket = new Socket()) { socket.bind(new InetSocketAddress("127.0.0.1", 0)); return true; }
            });
        }, "owned-boundary-control");
        thread.start(); thread.join(2000);
        if (thread.isAlive()) throw new IllegalStateException("Owned thread timeout");
    }
}
