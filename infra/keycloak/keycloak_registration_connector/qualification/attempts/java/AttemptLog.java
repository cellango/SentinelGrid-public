// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.lab.attempts;

import java.lang.reflect.Field;
import java.net.Socket;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/** Bootstrap-visible lab recorder. Never logs SQL, parameters, credentials or result values. */
public final class AttemptLog {
  private static final long PID = ProcessHandle.current().pid();
  private static final AtomicLong ids = new AtomicLong(), errors = new AtomicLong();
  private static long sequence;
  private static final ThreadLocal<ArrayDeque<Span>> spans =
      ThreadLocal.withInitial(ArrayDeque::new);
  private static final ThreadLocal<String> pending = new ThreadLocal<>();
  private static final ThreadLocal<Frame> server = new ThreadLocal<>();
  private static final ThreadLocal<String> calibration = new ThreadLocal<>();
  private static final Map<String, Long> clientCounts = new ConcurrentHashMap<>();
  private static final Map<String, Long> serverCounts = new ConcurrentHashMap<>();
  private static final ThreadLocal<Request> request = new ThreadLocal<>();
  private static final Map<Object, Request> sessions =
      Collections.synchronizedMap(new IdentityHashMap<>());

  private static final class Request {
    final long id = ids.incrementAndGet();
    String origin = "HTTP_UNCLASSIFIED";
  }

  private static final Set<Long> live = ConcurrentHashMap.newKeySet();
  private static final Path root = Path.of(System.getenv("SG_LAB_ROOT")).toAbsolutePath();
  private static final Path logs = Path.of(System.getenv("SG_LAB_ATTEMPT_LOGS")).toAbsolutePath();

  private record Span(
      long id,
      long parent,
      String origin,
      long request,
      String hook,
      String verb,
      String connection,
      long rpc,
      String testCase) {}

  private static final class Frame {
    final String connection;
    final Object session;
    long rpc;
    boolean read;

    Frame(String c, Object s) {
      connection = c;
      session = s;
    }
  }

  public static void start() throws Exception {
    if (!Files.isRegularFile(root.resolve("statement-observer-owned"))
        || !Files.isDirectory(logs)
        || !Files.isRegularFile(logs.resolve("attempt-report-owned")))
      throw new IllegalStateException("Owned disposable lab and report directory required");
    record("BOOT", 0, 0, "LAB", 0, "recorder", "NONE", "-", 0, "-", "OK");
    Runtime.getRuntime()
        .addShutdownHook(
            new Thread(
                () -> {
                  record(
                      "HEALTH",
                      0,
                      0,
                      "LAB",
                      0,
                      "recorder",
                      "NONE",
                      "-",
                      0,
                      "-",
                      "errors="
                          + errors.get()
                          + ",active="
                          + live.size()
                          + ",requests="
                          + sessions.size());
                },
                "sg-lab-attempt-health"));
  }

  public static void transformed(String name) {
    record("TRANSFORM", 0, 0, "LAB", 0, name, "NONE", "-", 0, "-", "OK");
  }

  public static void caught(Throwable error) {
    try {
      StackTraceElement top = error.getStackTrace()[0];
      Request r = request.get();
      record(
          "CAUGHT",
          0,
          0,
          r == null ? "UNKNOWN" : r.origin,
          r == null ? 0 : r.id,
          top.getClassName() + "." + top.getMethodName() + ":" + top.getLineNumber(),
          "ERROR_SITE",
          "-",
          0,
          "-",
          error.getClass().getName());
    } catch (Throwable e) {
      failure();
    }
  }

  public static long errorCount() {
    return errors.get();
  }

  public static void failure() {
    errors.incrementAndGet();
  }

  public static void caseStart(String name) {
    if (!name.matches("[a-z0-9_]{1,80}")) throw new IllegalArgumentException();
    calibration.set(name);
    record("CASE_START", 0, 0, "FIXTURE", 0, "case", "NONE", "-", 0, name, "OK");
  }

  public static void caseEnd() {
    String name = calibration.get();
    record("CASE_END", 0, 0, "FIXTURE", 0, "case", "NONE", "-", 0, name == null ? "-" : name, "OK");
    calibration.remove();
  }

  private static Object field(Object value, String name) {
    if (value == null) return null;
    for (Class<?> c = value.getClass(); c != null; c = c.getSuperclass()) {
      try {
        Field f = c.getDeclaredField(name);
        f.setAccessible(true);
        return f.get(value);
      } catch (NoSuchFieldException ignored) {
      } catch (ReflectiveOperationException | RuntimeException e) {
        errors.incrementAndGet();
        return null;
      }
    }
    return null;
  }

  private static String socket(Object transfer) {
    Object s = field(transfer, "socket");
    if (!(s instanceof Socket v)
        || !v.getInetAddress().isLoopbackAddress()
        || !v.getLocalAddress().isLoopbackAddress()) return "-";
    return Math.min(v.getLocalPort(), v.getPort()) + ":" + Math.max(v.getLocalPort(), v.getPort());
  }

  private static String connection(Object value, int depth) {
    if (value == null || depth > 4) return "-";
    String n = value.getClass().getName();
    if (n.equals("org.h2.value.Transfer")) return socket(value);
    for (String f : List.of("transfer", "conn", "session", "transferList", "command")) {
      Object nested = field(value, f);
      if (nested instanceof List<?> list) nested = list.size() == 1 ? list.getFirst() : null;
      String found = connection(nested, depth + 1);
      if (!found.equals("-")) return found;
    }
    return "-";
  }

  private static String sql(Object owner, Object[] args) {
    if (args.length > 0 && args[0] instanceof String s) return s;
    Object s = field(owner, "sql");
    if (!(s instanceof String)) s = field(owner, "sqlStatement");
    if (!(s instanceof String)) s = field(field(owner, "command"), "sql");
    return s instanceof String text ? text : "";
  }

  private static String verb(String hook, Object owner, Object[] args) {
    String method = hook.substring(hook.lastIndexOf('.') + 1);
    if (method.startsWith("set") && !method.equals("setAutoCommit"))
      return hook.contains("JdbcPreparedStatement") ? "BIND" : "SESSION";
    if (Set.of("commit", "rollback", "rollbackToSavepoint", "setSavepoint", "setAutoCommit")
        .contains(method)) return "TRANSACTION";
    if (method.equals("close") || method.equals("stop")) return "CLOSE";
    String s =
        sql(owner, args).replaceAll("(?s)/\\*.*?\\*/", " ").stripLeading().toUpperCase(Locale.ROOT);
    String first = s.split("[^A-Z_]", 2)[0];
    return switch (first) {
      case "SELECT", "TABLE", "VALUES", "EXPLAIN" -> "READ";
      case "INSERT",
              "UPDATE",
              "DELETE",
              "MERGE",
              "CREATE",
              "ALTER",
              "DROP",
              "TRUNCATE",
              "GRANT",
              "REVOKE",
              "COMMENT",
              "SET",
              "CALL" ->
          first;
      case "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE", "BEGIN" -> "TRANSACTION";
      default -> hook.contains(".ddl.") ? "DDL" : "UNKNOWN";
    };
  }

  public static long enter(Object owner, String hook, Object[] args) {
    try {
      ArrayDeque<Span> stack = spans.get();
      Span parent = stack.peek();
      long id = ids.incrementAndGet(), request = parent == null ? 0 : parent.request();
      String origin = parent == null ? "UNKNOWN" : parent.origin();
      if (hook.endsWith("AssociationResource.read")) origin = "OBSERVER";
      else if (hook.startsWith("org.keycloak.services.resources.admin.")) origin = "ADMIN";
      else if (hook.endsWith("TokenEndpoint.processGrantRequest")) origin = "ISSUER";
      else if (hook.endsWith("LabDatabase.main")
          || hook.startsWith("ai.sentinelgrid.keycloak.lab.attempts.AttemptCalibration."))
        origin = "FIXTURE";
      if (parent == null || !origin.equals(parent.origin())) request = id;
      Request context = AttemptLog.request.get();
      if (context != null) {
        if (hook.endsWith("AssociationResource.read")
            || hook.startsWith("org.keycloak.services.resources.admin.")
            || hook.endsWith("TokenEndpoint.processGrantRequest")) {
          context.origin = origin;
          record("HTTP_ROUTE", 0, 0, origin, context.id, "route", "NONE", "-", 0, "-", "OK");
        }
        origin = context.origin;
        request = context.id;
      }
      Frame frame = server.get();
      String c = frame == null ? connection(owner, 0) : frame.connection;
      long rpc = frame == null ? 0 : frame.rpc;
      Span span =
          new Span(
              id,
              parent == null ? 0 : parent.id(),
              origin,
              request,
              hook,
              verb(hook, owner, args),
              c,
              rpc,
              calibration.get() == null ? "-" : calibration.get());
      stack.push(span);
      live.add(id);
      recordSpan("ENTER", span, "OK");
      return id;
    } catch (Throwable e) {
      failure();
      return 0;
    }
  }

  public static void exit(long id, Throwable thrown) {
    try {
      if (id == 0) return;
      Span s = spans.get().poll();
      if (s == null || s.id() != id) {
        failure();
        return;
      }
      live.remove(id);
      String result = thrown == null ? "OK" : thrown.getClass().getName();
      recordSpan(thrown == null ? "EXIT" : "ERROR", s, result);
      if (spans.get().isEmpty()) spans.remove();
    } catch (Throwable e) {
      failure();
    }
  }

  private static void recordSpan(String event, Span s, String result) {
    Frame f = server.get();
    record(
        event,
        s.id(),
        s.parent(),
        s.origin(),
        s.request(),
        s.hook(),
        s.verb(),
        s.connection(),
        f == null ? s.rpc() : f.rpc,
        s.testCase(),
        result);
  }

  public static void trace(String operation) {
    if (!operation.matches("[A-Z_0-9]{1,64}")) {
      failure();
      return;
    }
    pending.set(operation);
  }

  public static void writeInt(Object transfer, int value) {
    try {
      String op = pending.get();
      if (op == null) {
        // Exact pinned H2 2.3.230 handshake callsite; no other integer/parameter is logged.
        boolean setId =
            value == 12
                && StackWalker.getInstance()
                    .walk(
                        s ->
                            s.anyMatch(
                                f ->
                                    f.getClassName().equals("org.h2.engine.SessionRemote")
                                        && f.getMethodName().equals("initTransfer")
                                        && f.getLineNumber() == 155));
        if (!setId) return;
        op = "SESSION_SET_ID";
      }
      pending.remove();
      String c = socket(transfer);
      long n = value == 12 ? 1 : clientCounts.merge(c, 1L, Long::sum);
      if (value == 12) clientCounts.put(c, 1L);
      Span s = spans.get().peek();
      Request context = request.get();
      record(
          "CLIENT_RPC",
          0,
          s == null ? 0 : s.id(),
          context != null ? context.origin : s == null ? "UNKNOWN" : s.origin(),
          context != null ? context.id : s == null ? 0 : s.request(),
          op,
          "PROTOCOL",
          c,
          n,
          calibration.get() == null ? "-" : calibration.get(),
          "OP_" + value);
    } catch (Throwable e) {
      failure();
    }
  }

  public static void serverEnter(Object owner) {
    try {
      if (server.get() != null) {
        failure();
        return;
      }
      server.set(new Frame(socket(field(owner, "transfer")), field(owner, "session")));
    } catch (Throwable e) {
      failure();
    }
  }

  public static void readInt(int value) {
    try {
      Frame f = server.get();
      if (f == null || f.read) return;
      f.read = true;
      f.rpc = value == 12 ? 1 : serverCounts.merge(f.connection, 1L, Long::sum);
      if (value == 12) serverCounts.put(f.connection, 1L);
      record(
          "SERVER_RPC",
          0,
          0,
          "SERVER",
          0,
          "opcode",
          "PROTOCOL",
          f.connection,
          f.rpc,
          "-",
          "OP_" + value);
    } catch (Throwable e) {
      failure();
    }
  }

  public static void serverExit(Throwable e) {
    Frame f = server.get();
    if (f != null)
      record(
          "SERVER_RPC_END",
          0,
          0,
          "SERVER",
          0,
          "frame",
          "PROTOCOL",
          f.connection,
          f.rpc,
          "-",
          e == null ? "OK" : e.getClass().getName());
    server.remove();
  }

  private static String transaction() {
    Frame f = server.get();
    Object t = f == null ? null : field(f.session, "transaction");
    return t == null ? "NONE" : field(t, "transactionId") + ":" + field(t, "sequenceNum");
  }

  private static Object currentSession(Object owner) throws Exception {
    Class<?> util =
        Class.forName(
            "org.keycloak.utils.KeycloakSessionUtil", false, owner.getClass().getClassLoader());
    Object session = util.getMethod("getKeycloakSession").invoke(null);
    // Arc may expose one CDI client proxy across concurrent requests. Key the actual context,
    // never the proxy, a worker thread, a URL, a header, or a caller-supplied correlation value.
    return session == null ? null : session.getClass().getMethod("getContext").invoke(session);
  }

  public static void httpAfterHandler(Object owner) {
    try {
      Object session = currentSession(owner);
      if (session == null) {
        failure();
        return;
      }
      Request r;
      synchronized (sessions) {
        r = sessions.computeIfAbsent(session, key -> new Request());
      }
      request.set(r);
      record("HTTP_CONTEXT", 0, 0, r.origin, r.id, "session", "NONE", "-", 0, "-", "OK");
    } catch (Throwable e) {
      failure();
    }
  }

  public static void httpBeforeClose(Object owner) {
    try {
      Request r = sessions.get(currentSession(owner));
      if (r != null) request.set(r);
      else request.remove();
    } catch (Throwable e) {
      failure();
      request.remove();
    }
  }

  public static void httpAfterClose(Object owner) {
    try {
      Object session = currentSession(owner);
      Request r = sessions.remove(session);
      if (r != null) record("HTTP_END", 0, 0, r.origin, r.id, "session", "NONE", "-", 0, "-", "OK");
    } catch (Throwable e) {
      failure();
    } finally {
      request.remove();
    }
  }

  public static void row(Object owner, Object oldRow, Object newRow) {
    try {
      Frame f = server.get();
      String table = String.valueOf(field(owner, "table"));
      if (!table.matches("[A-Z0-9_]+")) {
        failure();
        return;
      }
      record(
          "ROW",
          0,
          0,
          "SERVER",
          0,
          table,
          oldRow == null ? "INSERT" : newRow == null ? "DELETE" : "UPDATE",
          f == null ? "-" : f.connection,
          f == null ? 0 : f.rpc,
          "-",
          "OK");
    } catch (Throwable e) {
      failure();
    }
  }

  private static synchronized void record(
      String event,
      long id,
      long parent,
      String origin,
      long request,
      String hook,
      String verb,
      String connection,
      long rpc,
      String testCase,
      String result) {
    long n = ++sequence;
    try {
      Files.writeString(
          logs.resolve(PID + ".tsv"),
          String.join(
                  "\t",
                  Long.toString(PID),
                  Long.toString(n),
                  Long.toString(Thread.currentThread().threadId()),
                  event,
                  Long.toString(id),
                  Long.toString(parent),
                  origin,
                  Long.toString(request),
                  hook,
                  verb,
                  connection,
                  Long.toString(rpc),
                  testCase,
                  result,
                  server.get() == null ? "-" : String.valueOf(field(server.get().session, "id")),
                  transaction())
              + "\n",
          StandardOpenOption.CREATE,
          StandardOpenOption.APPEND);
    } catch (Throwable e) {
      errors.incrementAndGet();
    }
  }
}
