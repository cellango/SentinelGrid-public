// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.lab;

import java.nio.file.*;
import java.sql.*;
import org.h2.api.Trigger;

/** Test-only observer: records write attempts, including rolled-back attempts, without row data. */
public final class LabTrigger implements Trigger {
  private String table;

  public void init(
      Connection c, String schema, String trigger, String table, boolean before, int type) {
    this.table = table;
  }

  public void fire(Connection c, Object[] oldRow, Object[] newRow) throws SQLException {
    try {
      Path p = Path.of(System.getenv("SG_LAB_AUDIT_LOG"));
      if (!p.toAbsolutePath().startsWith(Path.of(System.getenv("SG_LAB_ROOT"))))
        throw new SQLException("Lab-only path required");
      synchronized (LabTrigger.class) {
        Files.writeString(
            p,
            table
                + "\t"
                + (oldRow == null ? "INSERT" : newRow == null ? "DELETE" : "UPDATE")
                + "\n",
            StandardOpenOption.CREATE,
            StandardOpenOption.APPEND);
      }
    } catch (Exception e) {
      throw new SQLException("Lab write observer unavailable", e);
    }
  }

  public void close() {}

  public void remove() {}
}
