// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.registration;

import org.keycloak.Config;
import org.keycloak.models.*;
import org.keycloak.services.resource.*;

/** Discovery alone admits nothing. Configuration is immutable and empty/disabled by default. */
public final class AssociationProviderFactory implements RealmResourceProviderFactory {
  private Grants grants = new Grants(false, "{\"version\":1,\"grants\":[]}");

  public void init(Config.Scope config) {
    String enabled = config.get("enabled", "false");
    if (!enabled.equals("true") && !enabled.equals("false"))
      throw new IllegalArgumentException("Invalid association enablement");
    grants =
        new Grants(
            Boolean.parseBoolean(enabled),
            config.get("grants-json", "{\"version\":1,\"grants\":[]}"));
  }

  public RealmResourceProvider create(KeycloakSession session) {
    Grants owned = grants;
    return new RealmResourceProvider() {
      public Object getResource() {
        return new AssociationResource(session, owned);
      }

      public void close() {}
    };
  }

  public String getId() {
    return "sentinelgrid-registration";
  }

  public void postInit(KeycloakSessionFactory factory) {}

  public void close() {}
}
