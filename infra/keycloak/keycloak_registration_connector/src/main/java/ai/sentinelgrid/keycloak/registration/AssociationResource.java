// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.registration;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.Response;
import java.net.URI;
import java.time.Instant;
import java.util.*;
import org.keycloak.models.*;
import org.keycloak.models.jpa.JpaUserProvider;
import org.keycloak.services.managers.AppAuthManager;
import org.keycloak.services.managers.AuthenticationManager.AuthResult;
import org.keycloak.storage.UserStoragePrivateUtil;

/** Prototype only: real native bearer verification; no creating/repairing model calls. */
@jakarta.enterprise.inject.Vetoed
@jakarta.ws.rs.ext.Provider
@Produces("application/json")
public final class AssociationResource {
  static final String AUDIENCE = "urn:sentinelgrid:issuer-association";
  static final String CONTRACT = "keycloak-registration-association-v1";
  static final String PERMISSION = "iam.read_workload_association";
  private final KeycloakSession session;
  private final Grants grants;

  AssociationResource(KeycloakSession session, Grants grants) {
    this.session = session;
    this.grants = grants;
  }

  @GET
  @Path("v1/clients/{client_uuid}/association")
  public Response read(@PathParam("client_uuid") String clientUuid, java.io.InputStream body) {
    try {
      if (!grants.enabled || grants.rows.isEmpty()) throw new IllegalArgumentException();
      Grants.uuid(clientUuid);
      var ctx = session.getContext();
      var realm = ctx.getRealm();
      var headers = ctx.getRequestHeaders();
      URI request = ctx.getUri().getRequestUri();
      String basePath = ctx.getUri().getBaseUri().getRawPath();
      // Keycloak hostname v2 may represent the root base path as an empty string.
      if (basePath.isEmpty()) basePath = "/";
      String expectedPath =
          basePath
              + "realms/"
              + realm.getName()
              + "/sentinelgrid-registration/v1/clients/"
              + clientUuid
              + "/association";
      if (!"GET".equals(ctx.getHttpRequest().getHttpMethod())
          || !"https".equals(request.getScheme())
          || request.getRawQuery() != null
          || !expectedPath.equals(request.getRawPath())
          || headers.getHeaderString("Cookie") != null
          || headers.getHeaderString("Transfer-Encoding") != null
          || !Set.of("0", "")
              .contains(Optional.ofNullable(headers.getHeaderString("Content-Length")).orElse("")))
        throw new IllegalArgumentException();
      for (String name :
          List.of(
              "x-tenant-id",
              "x-realm",
              "x-user-id",
              "x-internal-token",
              "x-internal-service-token"))
        if (headers.getHeaderString(name) != null) throw new IllegalArgumentException();
      String length = headers.getHeaderString("Content-Length");
      if (length != null && !length.equals("0")) throw new IllegalArgumentException();
      try {
        if (body == null || body.read() != -1) throw new IllegalArgumentException();
      } catch (java.io.IOException e) {
        throw new IllegalArgumentException();
      }
      var authHeaders = headers.getRequestHeader("Authorization");
      if (authHeaders == null
          || authHeaders.size() != 1
          || !authHeaders.getFirst().startsWith("Bearer ")) throw new IllegalArgumentException();
      String raw = authHeaders.getFirst().substring(7);
      if (raw.length() > 32768 || !raw.matches("[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+"))
        throw new IllegalArgumentException();
      String[] segments = raw.split("\\.");
      JsonNode header = decode(segments[0]), claims = decode(segments[1]);
      Grants.exact(header, Set.of("alg", "kid", "typ"));
      if (!"RS256".equals(Grants.text(header, "alg")) || !"JWT".equals(Grants.text(header, "typ")))
        throw new IllegalArgumentException();
      Grants.identifier(Grants.text(header, "kid"));
      if (!claims.isObject()) throw new IllegalArgumentException();
      // Pre-auth rejection only. Never allow session cleanup or username fallback in the native
      // stateless path.
      for (String name :
          List.of("sid", "session_state", "preferred_username", "act", "may_act", "sg_actor"))
        if (claims.has(name)) throw new IllegalArgumentException();
      String issuer = Grants.text(claims, "iss"),
          azp = Grants.text(claims, "azp"),
          sub = Grants.uuid(Grants.text(claims, "sub"));
      // Native service-account issuance may repeat azp as client_id; it grants no authority.
      if (claims.has("client_id") && !azp.equals(Grants.text(claims, "client_id")))
        throw new IllegalArgumentException();
      Grants.Grant grant =
          grants.rows.stream()
              .filter(
                  g ->
                      g.realmId().equals(realm.getId())
                          && g.issuer().equals(issuer)
                          && g.managementClientId().equals(azp)
                          && g.managementSubjectId().equals(sub)
                          && g.clientUuid().equals(clientUuid))
              .findFirst()
              .orElseThrow();
      validateClaims(claims, grant);
      if (!URI.create(grant.issuer()).getRawAuthority().equals(request.getRawAuthority()))
        throw new IllegalArgumentException();
      // Only Keycloak authenticates the submitted bytes. No custom signer, signature check or
      // auth-result injection.
      AuthResult auth =
          new AppAuthManager.BearerTokenAuthenticator(session)
              .setTokenString(raw)
              .setAudience(AUDIENCE)
              .authenticate();
      if (auth == null
          || auth.getSession() != null
          || auth.getUser() == null
          || auth.getClient() == null
          || !sub.equals(auth.getUser().getId())
          || !azp.equals(auth.getClient().getClientId())
          || !auth.getClient().getId().equals(auth.getUser().getServiceAccountClientLink())
          || auth.getUser().getFederationLink() != null
          || !auth.getClient().isServiceAccountsEnabled()) throw new IllegalArgumentException();
      var local = UserStoragePrivateUtil.userLocalStorage(session);
      if (!(local instanceof JpaUserProvider)) throw new IllegalArgumentException();
      ClientModel client = realm.getClientById(grant.clientUuid());
      UserModel user = local.getUserById(realm, grant.subjectId());
      requireAssociation(local, realm, client, user, grant);
      boolean clientEnabled = client.isEnabled(), subjectEnabled = user.isEnabled();
      // Repeat exact lookups to reject observable rebinding during the read; this is not an
      // atomic-snapshot claim.
      ClientModel againClient = realm.getClientById(grant.clientUuid());
      UserModel againUser = local.getUserById(realm, grant.subjectId());
      requireAssociation(local, realm, againClient, againUser, grant);
      if (clientEnabled != client.isEnabled()
          || subjectEnabled != user.isEnabled()
          || clientEnabled != againClient.isEnabled()
          || subjectEnabled != againUser.isEnabled()) throw new IllegalArgumentException();
      validateClaims(claims, grant); // Still within credential lifetime after model reads.
      Map<String, Object> result = new LinkedHashMap<>();
      result.put("contract", CONTRACT);
      result.put("issuer", grant.issuer());
      result.put("realm_id", grant.realmId());
      result.put("client_uuid", grant.clientUuid());
      result.put("client_id", grant.clientId());
      result.put("subject_id", grant.subjectId());
      result.put("tenant_id", grant.tenantId());
      result.put("client_enabled", clientEnabled);
      result.put("subject_enabled", subjectEnabled);
      result.put("observed_at", Instant.now().getEpochSecond());
      return response(200, result);
    } catch (RuntimeException e) {
      return response(503, Map.of("detail", "Association observation unavailable"));
    }
  }

  static void requireAssociation(
      UserProvider local,
      RealmModel realm,
      ClientModel client,
      UserModel user,
      Grants.Grant grant) {
    if (client == null
        || user == null
        || !grant.clientUuid().equals(client.getId())
        || !grant.clientId().equals(client.getClientId())
        || !client.isServiceAccountsEnabled()
        || !grant.subjectId().equals(user.getId())
        || user.getFederationLink() != null
        || !grant.clientUuid().equals(user.getServiceAccountClientLink()))
      throw new IllegalArgumentException();
    UserModel reciprocal = local.getServiceAccount(client);
    if (reciprocal == null
        || !grant.subjectId().equals(reciprocal.getId())
        || reciprocal.getFederationLink() != null
        || !grant.clientUuid().equals(reciprocal.getServiceAccountClientLink())
        || reciprocal.isEnabled() != user.isEnabled()) throw new IllegalArgumentException();
  }

  static void validateClaims(JsonNode p, Grants.Grant g) {
    long now = Instant.now().getEpochSecond(), iat = integer(p, "iat"), exp = integer(p, "exp");
    if (iat > now
        || now - iat > 60
        || exp <= now + 1
        || exp - iat < 1
        || exp - iat > 60
        || p.has("nbf") && integer(p, "nbf") > now
        || !"Bearer".equals(Grants.text(p, "typ"))
        || !g.tenantId().equals(Grants.text(p, "tenant_id"))
        || !"workload".equals(Grants.text(p, "sg_principal_type"))
        || !CONTRACT.equals(Grants.text(p, "sg_identity_contract"))
        || !p.path("sg_permissions").equals(Grants.JSON.valueToTree(List.of(PERMISSION))))
      throw new IllegalArgumentException();
    Grants.uuid(Grants.text(p, "jti"));
    JsonNode aud = p.get("aud");
    if (aud == null
        || !aud.isArray()
        || aud.size() != 2
        || !aud.get(0).isTextual()
        || !aud.get(1).isTextual()
        || !Set.of(g.iamAudience(), AUDIENCE)
            .equals(new HashSet<>(List.of(aud.get(0).textValue(), aud.get(1).textValue()))))
      throw new IllegalArgumentException();
    if (p.has("realm_access")
            && !p.get("realm_access").equals(Grants.JSON.valueToTree(Map.of("roles", List.of())))
        || p.has("resource_access")
            && !p.get("resource_access").equals(Grants.JSON.createObjectNode())
        || p.has("scope") && (!p.get("scope").isTextual() || !p.get("scope").textValue().isEmpty()))
      throw new IllegalArgumentException();
    Map<String, String> target =
        Map.of(
            "issuer",
            g.issuer(),
            "client_uuid",
            g.clientUuid(),
            "client_id",
            g.clientId(),
            "subject_id",
            g.subjectId(),
            "tenant_id",
            g.tenantId());
    if (!p.path("sg_registration_target").equals(Grants.JSON.valueToTree(target)))
      throw new IllegalArgumentException();
  }

  static long integer(JsonNode p, String field) {
    JsonNode v = p.get(field);
    if (v == null || !v.isIntegralNumber() || !v.canConvertToLong())
      throw new IllegalArgumentException();
    return v.longValue();
  }

  static JsonNode decode(String value) {
    try {
      byte[] b = Base64.getUrlDecoder().decode(value);
      if (!Base64.getUrlEncoder().withoutPadding().encodeToString(b).equals(value))
        throw new IllegalArgumentException();
      return Grants.JSON.readTree(b);
    } catch (Exception e) {
      throw new IllegalArgumentException();
    }
  }

  private static Response response(int status, Object body) {
    return Response.status(status)
        .type("application/json")
        .header("Cache-Control", "no-store")
        .header("Pragma", "no-cache")
        .header("X-Content-Type-Options", "nosniff")
        .entity(body)
        .build();
  }
}
