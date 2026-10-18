// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.lab;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.*;
import java.util.*;

/** Lab-only JDBC controls, not application/vendor schema migrations or an exposed endpoint. */
public final class LabDatabase {
  static String hash(String s) throws Exception {
    return HexFormat.of()
        .formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));
  }

  private static final String SUBJECT = "22222222-2222-4222-8222-222222222222";

  private static String quote(String name) {
    if (!name.matches("[A-Z_]+"))
      throw new IllegalArgumentException("Unexpected vendor identifier");
    return "\"" + name + "\"";
  }

  private static String literal(Object v) {
    if (v == null) return "NULL";
    if (v instanceof Number || v instanceof Boolean) return v.toString();
    if (!(v instanceof String))
      throw new IllegalArgumentException("Unsupported synthetic backup value");
    return "'" + v.toString().replace("'", "''") + "'";
  }

  private static void backupRows(Connection c, String table, String column, StringBuilder sql)
      throws Exception {
    try (var s =
        c.prepareStatement("SELECT * FROM " + quote(table) + " WHERE " + quote(column) + "=?")) {
      s.setString(1, SUBJECT);
      try (var r = s.executeQuery()) {
        while (r.next()) {
          List<String> names = new ArrayList<>(), values = new ArrayList<>();
          for (int i = 1; i <= r.getMetaData().getColumnCount(); i++) {
            names.add(quote(r.getMetaData().getColumnName(i)));
            values.add(literal(r.getObject(i)));
          }
          sql.append("INSERT INTO ")
              .append(quote(table))
              .append(" (")
              .append(String.join(",", names))
              .append(") VALUES (")
              .append(String.join(",", values))
              .append(");\n");
        }
      }
    }
  }

  private static void subjectFixture(Connection c, boolean backup) throws Exception {
    java.nio.file.Path root =
        java.nio.file.Path.of(System.getenv("SG_LAB_ROOT")).toAbsolutePath().normalize();
    if (!java.nio.file.Files.exists(root.resolve("statement-observer-owned"))
        || System.getenv("SG_LAB_FIXTURE_NONCE") == null)
      throw new IllegalArgumentException("Fresh controlled lab required");
    List<String[]> keys = new ArrayList<>();
    try (var r = c.getMetaData().getExportedKeys(null, "PUBLIC", "USER_ENTITY")) {
      while (r.next())
        keys.add(new String[] {r.getString("FKTABLE_NAME"), r.getString("FKCOLUMN_NAME")});
    }
    if (backup) {
      StringBuilder sql = new StringBuilder();
      backupRows(c, "USER_ENTITY", "ID", sql);
      for (String[] key : keys) backupRows(c, key[0], key[1], sql);
      java.nio.file.Files.writeString(root.resolve("subject-fixture-backup.sql"), sql.toString());
    } else {
      for (String[] key : keys)
        try (var s =
            c.prepareStatement("DELETE FROM " + quote(key[0]) + " WHERE " + quote(key[1]) + "=?")) {
          s.setString(1, SUBJECT);
          s.executeUpdate();
        }
      try (var s = c.prepareStatement("DELETE FROM USER_ENTITY WHERE ID=?")) {
        s.setString(1, SUBJECT);
        if (s.executeUpdate() != 1) throw new IllegalStateException("Synthetic subject missing");
      }
    }
  }

  public static void main(String[] args) throws Exception {
    String url = System.getenv("SG_LAB_JDBC");
    if (url == null || !url.matches("jdbc:h2:tcp://127\\.0\\.0\\.1:[0-9]+/\\./sglab;.*"))
      throw new IllegalArgumentException("New loopback lab only");
    String fixtureNonce = System.getenv("SG_LAB_FIXTURE_NONCE");
    java.nio.file.Path initialized =
        fixtureNonce == null
            ? null
            : java.nio.file.Path.of(System.getenv("SG_LAB_ROOT"))
                .resolve("fixture-connection-initialized");
    String connectionUrl =
        fixtureNonce == null || !java.nio.file.Files.exists(initialized)
            ? url
            : url.substring(0, url.indexOf(';'));
    try (Connection c =
        DriverManager.getConnection(connectionUrl, "sa", System.getenv("SG_LAB_DB_PASSWORD"))) {
      if (initialized != null)
        java.nio.file.Files.writeString(initialized, "created by disposable fixture helper");
      if (fixtureNonce != null)
        try (var tag = c.prepareStatement("SET @SG_LAB_FIXTURE = ?")) {
          tag.setString(1, fixtureNonce);
          tag.execute();
        }
      List<String> tables = new ArrayList<>();
      try (var r =
          c.createStatement()
              .executeQuery(
                  "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='PUBLIC' AND"
                      + " TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")) {
        while (r.next()) tables.add(r.getString(1));
      }
      if (args[0].equals("backup-subject") || args[0].equals("delete-subject")) {
        subjectFixture(c, args[0].equals("backup-subject"));
      } else if (args[0].equals("observer-health")) {
        try (var r = c.createStatement().executeQuery("CALL SG_OBSERVER_HEALTH()")) {
          r.next();
          System.out.println(r.getString(1));
        }
      } else if (args[0].equals("install")) {
        if (System.getenv("SG_LAB_FIXTURE_NONCE") != null)
          c.createStatement()
              .execute(
                  "CREATE ALIAS IF NOT EXISTS SG_OBSERVER_HEALTH FOR"
                      + " 'ai.sentinelgrid.keycloak.lab.LabStatementListener.health'");
        for (String t : tables)
          c.createStatement()
              .execute(
                  "CREATE TRIGGER IF NOT EXISTS SG_OBS_"
                      + t
                      + " BEFORE INSERT, UPDATE, DELETE ON \""
                      + t
                      + "\" FOR EACH ROW CALL 'ai.sentinelgrid.keycloak.lab.LabTrigger'");
        System.out.println(tables.size());
      } else if (args[0].equals("snapshot")) {
        for (String t : tables) {
          List<String> rows = new ArrayList<>();
          try (var r = c.createStatement().executeQuery("SELECT * FROM \"" + t + "\"")) {
            int n = r.getMetaData().getColumnCount();
            while (r.next()) {
              StringBuilder value = new StringBuilder();
              for (int i = 1; i <= n; i++) {
                Object v = r.getObject(i);
                String s;
                if (v == null) s = "null";
                else if (v instanceof byte[] b) s = HexFormat.of().formatHex(b);
                else if (v instanceof java.sql.Clob b) s = b.getSubString(1, (int) b.length());
                else if (v instanceof java.sql.Blob b)
                  s = HexFormat.of().formatHex(b.getBytes(1, (int) b.length()));
                else s = v.toString();
                value.append(s.length()).append(':').append(s).append(';');
              }
              rows.add(hash(value.toString()));
            }
          }
          Collections.sort(rows);
          System.out.println(t + "\t" + rows.size() + "\t" + hash(String.join("\n", rows)));
        }
      } else if (args[0].equals("sql")) {
        // Explicit lab fixture setup only; never called by the provider or an observation request.
        String sql = java.nio.file.Files.readString(java.nio.file.Path.of(args[1]));
        try (var s = c.createStatement();
            var reader = new org.h2.util.ScriptReader(new java.io.StringReader(sql))) {
          String statement;
          while ((statement = reader.readStatement()) != null) {
            s.execute(statement.strip());
          }
        }
      } else throw new IllegalArgumentException("Unknown lab command");
    }
  }
}
