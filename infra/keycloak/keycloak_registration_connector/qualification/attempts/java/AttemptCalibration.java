// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.lab.attempts;

import java.nio.file.*;
import java.sql.*;
import java.util.*;

/** Synthetic fixture effects only, never invoked by the provider or application. */
public final class AttemptCalibration {
  private static final List<String> results = new ArrayList<>();

  private static String jdbc() {
    String u = System.getenv("SG_LAB_JDBC");
    if (u == null || !u.matches("jdbc:h2:tcp://127\\.0\\.0\\.1:[0-9]+/\\./sglab;.*"))
      throw new IllegalStateException("New owned loopback lab required");
    return u.substring(0, u.indexOf(';'));
  }

  private static Connection open() throws SQLException {
    return DriverManager.getConnection(jdbc(), "sa", System.getenv("SG_LAB_DB_PASSWORD"));
  }

  private interface Checked {
    void run() throws Exception;
  }

  private static void one(String name, Checked f) throws Exception {
    AttemptLog.caseStart(name);
    try {
      f.run();
      results.add(name);
    } finally {
      AttemptLog.caseEnd();
    }
  }

  private static void require(boolean value) {
    if (!value) throw new IllegalStateException("Synthetic calibration assertion failed");
  }

  private static void rejected(Checked f) throws Exception {
    try {
      f.run();
      throw new IllegalStateException("Expected genuine JDBC rejection");
    } catch (SQLException expected) {
      require(expected.getSQLState() != null);
    }
  }

  private static int count(Connection c, int id) throws SQLException {
    try (var p = c.prepareStatement("SELECT COUNT(*) FROM SG_ATTEMPT_T WHERE ID=?")) {
      p.setInt(1, id);
      try (var r = p.executeQuery()) {
        r.next();
        return r.getInt(1);
      }
    }
  }

  public static void nestedDDL(Connection c) throws SQLException {
    try (var s = c.createStatement()) {
      s.execute("CREATE TABLE SG_ATTEMPT_NESTED (ID INT)");
      s.execute("ALTER TABLE SG_ATTEMPT_NESTED ADD VALUE2 INT");
      s.execute("DROP TABLE SG_ATTEMPT_NESTED");
    }
  }

  private static volatile Thread background;

  public static void delayedWrite() {
    AttemptLog.caseStart("delayed_background_write");
    try {
      Path returned = Path.of(System.getenv("SG_LAB_ROOT")).resolve("attempt-schedule-returned");
      long deadline = System.nanoTime() + 4_000_000_000L;
      while (!Files.exists(returned)) {
        if (System.nanoTime() > deadline)
          throw new IllegalStateException("Delayed fixture deadline");
        Thread.sleep(10);
      }
      try (var c = open();
          var s = c.createStatement()) {
        require(s.executeUpdate("INSERT INTO SG_ATTEMPT_T(ID) VALUES(30)") == 1);
      }
    } catch (Exception e) {
      throw new RuntimeException("Synthetic background failure", e);
    } finally {
      AttemptLog.caseEnd();
    }
  }

  public static void scheduleBackground() {
    background = new Thread(AttemptCalibration::delayedWrite, "sg-owned-delayed-fixture");
    background.start();
  }

  public static void awaitBackground() throws Exception {
    background.join(4000);
    require(!background.isAlive());
  }

  public static void main(String[] args) throws Exception {
    if (args.length != 1) throw new IllegalArgumentException();
    if (args[0].equals("logger-failure")) {
      AttemptLog.caseStart("logger_failure_detection");
      Path file =
          Path.of(System.getenv("SG_LAB_ATTEMPT_LOGS"))
              .resolve(ProcessHandle.current().pid() + ".tsv");
      Path backup = file.resolveSibling(file.getFileName() + ".preserved");
      long before = AttemptLog.errorCount();
      Files.move(file, backup);
      Files.createDirectory(file);
      try {
        AttemptLog.caseStart("intentionally_lost_record");
      } finally {
        Files.delete(file);
        Files.move(backup, file);
      }
      require(AttemptLog.errorCount() > before);
      AttemptLog.caseEnd();
      System.out.println(
          "{\"logger_failure_pid\":"
              + ProcessHandle.current().pid()
              + ",\"logger_failure_detected\":true}");
      return;
    }
    try (var c = open();
        var s = c.createStatement()) {
      if (args[0].equals("crash-commit")) {
        c.setAutoCommit(false);
        s.executeUpdate("INSERT INTO SG_ATTEMPT_T(ID) VALUES(99)");
        Path root = Path.of(System.getenv("SG_LAB_ROOT"));
        Files.writeString(root.resolve("attempt-crash-ready"), "new synthetic transaction");
        long deadline = System.nanoTime() + 20_000_000_000L;
        while (!Files.exists(root.resolve("attempt-crash-release"))) {
          if (System.nanoTime() > deadline) throw new IllegalStateException("Lab deadline");
          Thread.sleep(10);
        }
        one("commit_after_actual_server_death", () -> rejected(c::commit));
        System.out.println("{\"commit_rejected_after_actual_outage\":true}");
        return;
      }
      if (args[0].equals("recover")) {
        one("uncommitted_row_absent_after_restart", () -> require(count(c, 99) == 0));
        s.execute("DROP TABLE SG_ATTEMPT_T");
        System.out.println("{\"uncommitted_row_absent_after_restart\":true}");
        return;
      }
      if (!args[0].equals("normal")) throw new IllegalArgumentException();
      s.execute("CREATE TABLE SG_ATTEMPT_T (ID INT PRIMARY KEY)");
      s.execute(
          "CREATE TRIGGER SG_ATTEMPT_ROW BEFORE INSERT,UPDATE,DELETE ON SG_ATTEMPT_T"
              + " FOR EACH ROW CALL 'ai.sentinelgrid.keycloak.lab.LabTrigger'");
      s.execute("INSERT INTO SG_ATTEMPT_T(ID) VALUES(1)");
      one("valid_select", () -> require(count(c, 1) == 1));
      one(
          "sql_and_parameter_canary",
          () -> {
            String canary = System.getenv("SG_LAB_ATTEMPT_CANARY");
            require(canary != null && canary.length() >= 24);
            try (var p = c.prepareStatement("SELECT ? /* " + canary + " */")) {
              p.setString(1, canary);
              try (var r = p.executeQuery()) {
                require(r.next() && canary.equals(r.getString(1)));
              }
            }
          });
      one("server_parse_failure", () -> rejected(() -> c.prepareStatement("NOT VALID SQL")));
      one(
          "client_missing_parameter",
          () -> {
            try (var p = c.prepareStatement("VALUES(?)")) {
              rejected(p::executeQuery);
            }
          });
      one(
          "client_bad_bind_index",
          () -> {
            try (var p = c.prepareStatement("VALUES(?)")) {
              rejected(() -> p.setInt(2, 1));
            }
          });
      one(
          "constraint_failure",
          () -> rejected(() -> s.executeUpdate("INSERT INTO SG_ATTEMPT_T(ID) VALUES(1)")));
      one(
          "zero_row_update_delete",
          () -> {
            require(s.executeUpdate("UPDATE SG_ATTEMPT_T SET ID=3 WHERE ID=2") == 0);
            require(s.executeUpdate("DELETE FROM SG_ATTEMPT_T WHERE ID=2") == 0);
          });
      one(
          "row_rollback",
          () -> {
            c.setAutoCommit(false);
            require(s.executeUpdate("UPDATE SG_ATTEMPT_T SET ID=2 WHERE ID=1") == 1);
            c.rollback();
            c.setAutoCommit(true);
            require(count(c, 1) == 1 && count(c, 2) == 0);
          });
      one(
          "savepoint_rollback",
          () -> {
            c.setAutoCommit(false);
            Savepoint sp = c.setSavepoint();
            s.executeUpdate("INSERT INTO SG_ATTEMPT_T(ID) VALUES(2)");
            c.rollback(sp);
            c.commit();
            c.setAutoCommit(true);
            require(count(c, 2) == 0);
          });
      one(
          "batch_partial_failure",
          () -> {
            try (var p = c.prepareStatement("INSERT INTO SG_ATTEMPT_T(ID) VALUES(?)")) {
              p.setInt(1, 10);
              p.addBatch();
              p.setInt(1, 1);
              p.addBatch();
              rejected(p::executeBatch);
            }
            require(count(c, 10) == 1);
            s.executeUpdate("DELETE FROM SG_ATTEMPT_T WHERE ID=10");
          });
      one(
          "merge_update",
          () -> {
            require(s.executeUpdate("MERGE INTO SG_ATTEMPT_T(ID) KEY(ID) VALUES(1)") == 1);
          });
      one(
          "ddl_implicit_commit",
          () -> {
            c.setAutoCommit(false);
            s.executeUpdate("INSERT INTO SG_ATTEMPT_T(ID) VALUES(2)");
            s.execute("CREATE TABLE SG_ATTEMPT_DDL(ID INT)");
            c.rollback();
            c.setAutoCommit(true);
            require(count(c, 2) == 1);
            s.execute("ALTER TABLE SG_ATTEMPT_DDL ADD EXTRA INT");
            s.execute("DROP TABLE SG_ATTEMPT_DDL");
            s.executeUpdate("DELETE FROM SG_ATTEMPT_T WHERE ID=2");
          });
      s.execute(
          "CREATE ALIAS SG_ATTEMPT_NEST FOR "
              + "'ai.sentinelgrid.keycloak.lab.attempts.AttemptCalibration.nestedDDL'");
      one("nested_internal_ddl", () -> s.execute("CALL SG_ATTEMPT_NEST()"));
      s.execute("DROP ALIAS SG_ATTEMPT_NEST");
      one(
          "prepared_statement_recompile",
          () -> {
            try (var p = c.prepareStatement("SELECT * FROM SG_ATTEMPT_T WHERE ID=?")) {
              p.setInt(1, 1);
              try (var r = p.executeQuery()) {
                require(r.next());
              }
              try (var other = open();
                  var stmt = other.createStatement()) {
                stmt.execute("ALTER TABLE SG_ATTEMPT_T ADD EXTRA INT");
              }
              try (var r = p.executeQuery()) {
                require(r.next());
              }
            }
          });
      s.execute(
          "CREATE ALIAS SG_ATTEMPT_SCHEDULE FOR "
              + "'ai.sentinelgrid.keycloak.lab.attempts.AttemptCalibration.scheduleBackground'");
      s.execute(
          "CREATE ALIAS SG_ATTEMPT_AWAIT FOR "
              + "'ai.sentinelgrid.keycloak.lab.attempts.AttemptCalibration.awaitBackground'");
      one(
          "delayed_effect_after_response",
          () -> {
            s.execute("CALL SG_ATTEMPT_SCHEDULE()");
            Files.writeString(
                Path.of(System.getenv("SG_LAB_ROOT")).resolve("attempt-schedule-returned"),
                "Caller received the scheduled response");
            s.execute("CALL SG_ATTEMPT_AWAIT()");
            require(count(c, 30) == 1);
            s.executeUpdate("DELETE FROM SG_ATTEMPT_T WHERE ID=30");
          });
      s.execute("DROP ALIAS SG_ATTEMPT_SCHEDULE");
      s.execute("DROP ALIAS SG_ATTEMPT_AWAIT");
      one(
          "client_closed_connection_commit",
          () -> {
            var closed = open();
            closed.close();
            rejected(closed::commit);
          });
      String password = UUID.randomUUID().toString();
      s.execute("CREATE USER SG_ATTEMPT_READER PASSWORD '" + password + "'");
      s.execute("GRANT SELECT ON SG_ATTEMPT_T TO SG_ATTEMPT_READER");
      one(
          "server_authorization_failure",
          () -> {
            try (var limited = DriverManager.getConnection(jdbc(), "SG_ATTEMPT_READER", password);
                var stmt = limited.createStatement()) {
              rejected(() -> stmt.executeUpdate("DELETE FROM SG_ATTEMPT_T WHERE ID=1"));
            }
          });
      s.execute("DROP USER SG_ATTEMPT_READER");
      System.out.println("{\"cases_passed\":[\"" + String.join("\",\"", results) + "\"]}");
    }
  }
}
