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

  public static void main(String[] args) throws Exception {
    String url = System.getenv("SG_LAB_JDBC");
    if (url == null || !url.matches("jdbc:h2:tcp://127\\.0\\.0\\.1:[0-9]+/\\./sglab;.*"))
      throw new IllegalArgumentException("New loopback lab only");
    try (Connection c =
        DriverManager.getConnection(url, "sa", System.getenv("SG_LAB_DB_PASSWORD"))) {
      List<String> tables = new ArrayList<>();
      try (var r =
          c.createStatement()
              .executeQuery(
                  "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='PUBLIC' AND"
                      + " TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")) {
        while (r.next()) tables.add(r.getString(1));
      }
      if (args[0].equals("install")) {
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
        try (var s = c.createStatement()) {
          s.execute(sql);
        }
      } else throw new IllegalArgumentException("Unknown lab command");
    }
  }
}
