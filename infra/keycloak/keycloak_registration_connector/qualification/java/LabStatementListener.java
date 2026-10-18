// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.lab;

import java.nio.file.*;
import java.sql.SQLException;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicLong;
import org.h2.api.DatabaseEventListener;

/**
 * New-lab-only SQL observer and deterministic pause. Never changes authentication or query results.
 */
public final class LabStatementListener implements DatabaseEventListener {
  private static final AtomicLong sequence = new AtomicLong();
  private static final AtomicLong failures = new AtomicLong();

  public static String source() {
    return channel("");
  }

  public static String health() {
    return sequence.get() + ":" + failures.get();
  }

  private static Path root() {
    Path p = Path.of(System.getenv("SG_LAB_ROOT")).toAbsolutePath().normalize();
    if (!Files.isDirectory(p) || !Files.exists(p.resolve("statement-observer-owned")))
      throw new IllegalStateException("Disposable lab marker missing");
    return p;
  }

  private static final class LocalSession {
    static final java.lang.reflect.Method CURRENT;

    static {
      try {
        CURRENT = org.h2.engine.SessionLocal.class.getDeclaredMethod("getThreadLocalSession");
        CURRENT.setAccessible(true);
      } catch (Exception e) {
        throw new ExceptionInInitializerError(e);
      }
    }
  }

  private static String channel(String ignoredSql) {
    String nonce = System.getenv("SG_LAB_FIXTURE_NONCE");
    if (nonce == null) return "UNMARKED";
    try {
      Object current = LocalSession.CURRENT.invoke(null);
      if (current instanceof org.h2.engine.SessionLocal session
          && nonce.equals(session.getVariable("SG_LAB_FIXTURE").getString())) return "FIXTURE";
      return "UNMARKED";
    } catch (Exception e) {
      failures.incrementAndGet();
      return "UNATTRIBUTED";
    }
  }

  private static String verb(String sql) {
    String s = sql.replaceAll("(?s)/\\*.*?\\*/", " ").stripLeading().toUpperCase(Locale.ROOT);
    String first = s.split("[^A-Z_]", 2)[0];
    return switch (first) {
      case "SELECT", "TABLE", "VALUES", "EXPLAIN" -> "READ";
      case "INSERT",
              "UPDATE",
              "DELETE",
              "MERGE",
              "TRUNCATE",
              "CREATE",
              "ALTER",
              "DROP",
              "GRANT",
              "REVOKE",
              "COMMENT" ->
          first;
      case "COMMIT", "ROLLBACK", "BEGIN", "SAVEPOINT", "RELEASE" -> "TRANSACTION";
      case "SET" ->
          s.matches(
                      "SET (NON_KEYWORDS|QUERY_TIMEOUT|LOCK_TIMEOUT|SCHEMA|TRANSACTION|AUTOCOMMIT|READONLY)\\b.*")
                  || s.matches("SET @SG_LAB_FIXTURE.*")
              ? "SESSION_SETTING"
              : "SET";
      default -> "OTHER";
    };
  }

  private static String shape(String sql) {
    String s = sql.toUpperCase(Locale.ROOT).replace('"', ' ').replaceAll("\\s+", " ");
    if (s.matches("(?s).*WHERE\\s+(?:[A-Z0-9_]+\\.)?SERVICE_ACCOUNT_CLIENT_LINK\\s*=.*"))
      return "SERVICE_ACCOUNT_LOOKUP";
    if (s.contains("FROM USER_ENTITY") && s.matches("(?s).*WHERE\\s+(?:[A-Z0-9_]+\\.)?ID\\s*=.*"))
      return "USER_BY_ID";
    if (s.contains("FROM CLIENT_ENTITY")) return "CLIENT";
    return "OTHER";
  }

  private static synchronized void record(String event, String verb, String channel, String shape) {
    long n = sequence.incrementAndGet();
    try {
      Files.writeString(
          root().resolve("statements.tsv"),
          ProcessHandle.current().pid()
              + "\t"
              + n
              + "\t"
              + event
              + "\t"
              + verb
              + "\t"
              + channel
              + "\t"
              + shape
              + "\n",
          StandardOpenOption.CREATE,
          StandardOpenOption.APPEND);
    } catch (Exception e) {
      failures.incrementAndGet();
    }
  }

  private static final Object barrierLock = new Object();

  private static void pause(String event, String shape, String channel) {
    if (!channel.equals("UNMARKED")) return;
    try {
      Path r = root(), control = r.resolve("barrier.control");
      if (!Files.exists(control)) return;
      synchronized (barrierLock) {
        if (!Files.exists(control)) return;
        String[] expected = Files.readString(control).strip().split("\t");
        if (expected.length != 3 || !expected[0].equals(event) || !expected[1].equals(shape))
          return;
        Path seen = r.resolve("barrier.seen");
        int count = (Files.exists(seen) ? Integer.parseInt(Files.readString(seen)) : 0) + 1;
        Files.writeString(seen, Integer.toString(count));
        if (count < Integer.parseInt(expected[2])) return;
        Files.move(control, r.resolve("barrier.claimed"), StandardCopyOption.ATOMIC_MOVE);
        Files.writeString(r.resolve("barrier.entered"), event + "\t" + shape + "\t" + count);
      }
      long deadline = System.nanoTime() + 8_000_000_000L;
      while (!Files.exists(r.resolve("barrier.release"))) {
        if (System.nanoTime() > deadline) {
          Files.writeString(r.resolve("barrier.timeout"), "timeout");
          return;
        }
        Thread.sleep(10);
      }
    } catch (Exception e) {
      failures.incrementAndGet();
    }
  }

  @Override
  public void setProgress(int state, String sql, long x, long max) {
    if (state != STATE_STATEMENT_START && state != STATE_STATEMENT_END) return;
    String c = channel(sql),
        v = verb(sql),
        s = shape(sql),
        event = state == STATE_STATEMENT_START ? "START" : "END";
    record(event, v, c, s);
    pause(event, s, c);
  }

  @Override
  public void exceptionThrown(SQLException error, String sql) {
    record(
        "ERROR",
        verb(sql == null ? "" : sql),
        channel(sql == null ? "" : sql),
        "SQLSTATE_" + error.getSQLState());
  }
}
