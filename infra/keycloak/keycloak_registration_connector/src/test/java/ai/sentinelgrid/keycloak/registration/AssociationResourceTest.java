// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.registration;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.node.ObjectNode;
import jakarta.ws.rs.core.HttpHeaders;
import jakarta.ws.rs.core.Response;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.time.Instant;
import java.util.*;
import java.util.stream.Stream;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.*;
import org.keycloak.common.ClientConnection;
import org.keycloak.crypto.*;
import org.keycloak.http.HttpRequest;
import org.keycloak.models.*;
import org.keycloak.models.jpa.JpaUserProvider;
import org.keycloak.storage.DatastoreProvider;
import org.keycloak.storage.datastore.*;

/**
 * Actual AppAuthManager/TokenVerifier/RS256. Only keys, request/context and SDK storage are
 * doubles. No real Keycloak server, SQL, federation, provider installation or non-mutation proof.
 */
class AssociationResourceTest {
  static final String ISSUER = "https://identity.internal.test/realms/synthetic",
      REALM = "fixture-realm";
  static final String TENANT = "11111111-1111-4111-8111-111111111111",
      SUBJECT = "22222222-2222-4222-8222-222222222222";
  static final String CLIENT = "33333333-3333-4333-8333-333333333333",
      MANAGEMENT = "44444444-4444-4444-8444-444444444444";
  static final String MANAGEMENT_CLIENT = "55555555-5555-4555-8555-555555555555",
      FOREIGN = "66666666-6666-4666-8666-666666666666";
  static KeyPair key, other;
  KeycloakSession session;
  KeycloakContext context;
  KeycloakUriInfo uri;
  HttpHeaders headers;
  HttpRequest request;
  RealmModel realm;
  ClientModel client, managementClient;
  UserModel user, management;
  UserProvider nativeUsers;
  JpaUserProvider local;
  DefaultDatastoreProvider datastore;
  SingleUseObjectProvider revoked;
  SignatureProvider signature;
  List<Object> mocks;
  java.io.InputStream body;
  ObjectNode claims;
  Map<String, Object> grant;
  AssociationResource resource;
  int targetReads, signatureChecks;
  Map<String, List<String>> incoming;

  @BeforeAll
  static void keys() throws Exception {
    org.keycloak.common.Profile.configure();
    KeyPairGenerator g = KeyPairGenerator.getInstance("RSA");
    g.initialize(2048);
    key = g.generateKeyPair();
    other = g.generateKeyPair();
  }

  <T> T sdk(Class<T> type) {
    T m =
        mock(
            type,
            invocation -> {
              String method = invocation.getMethod().getName();
              if (method.matches(
                  "^(set|add|remove|delete|create|update|grant|revoke|persist|merge|flush|enable|close).*")) {
                if (!(type == KeycloakSession.class
                    && method.equals("setAttribute")
                    && invocation.getArgument(0).equals("state_checker")))
                  throw new AssertionError("Forbidden SDK mutation: " + method);
              }
              return RETURNS_DEFAULTS.answer(invocation);
            });
    mocks.add(m);
    return m;
  }

  @BeforeEach
  void setup() throws Exception {
    body = new java.io.ByteArrayInputStream(new byte[0]);
    mocks = new ArrayList<>();
    incoming = new HashMap<>();
    session = sdk(KeycloakSession.class);
    context = sdk(KeycloakContext.class);
    uri = sdk(KeycloakUriInfo.class);
    headers = sdk(HttpHeaders.class);
    request = sdk(HttpRequest.class);
    realm = sdk(RealmModel.class);
    client = sdk(ClientModel.class);
    managementClient = sdk(ClientModel.class);
    user = sdk(UserModel.class);
    management = sdk(UserModel.class);
    nativeUsers = sdk(UserProvider.class);
    local = sdk(JpaUserProvider.class);
    datastore = sdk(DefaultDatastoreProvider.class);
    revoked = sdk(SingleUseObjectProvider.class);
    signature = sdk(SignatureProvider.class);
    when(session.getContext()).thenReturn(context);
    when(context.getRealm()).thenReturn(realm);
    when(context.getUri()).thenReturn(uri);
    when(context.getRequestHeaders()).thenReturn(headers);
    when(context.getHttpRequest()).thenReturn(request);
    when(context.getConnection()).thenReturn(sdk(ClientConnection.class));
    when(uri.getBaseUri()).thenReturn(URI.create("https://identity.internal.test/"));
    when(uri.getRequestUri())
        .thenReturn(
            URI.create(
                ISSUER + "/sentinelgrid-registration/v1/clients/" + CLIENT + "/association"));
    when(request.getHttpMethod()).thenReturn("GET");
    when(realm.getName()).thenReturn("synthetic");
    when(realm.getId()).thenReturn(REALM);
    when(headers.getRequestHeader(anyString())).thenAnswer(a -> incoming.get(a.getArgument(0)));
    when(headers.getHeaderString(anyString()))
        .thenAnswer(
            a -> {
              var v = incoming.get(a.getArgument(0));
              return v == null ? null : String.join(",", v);
            });
    when(session.users()).thenReturn(nativeUsers);
    when(session.singleUseObjects()).thenReturn(revoked);
    when(nativeUsers.getUserById(realm, MANAGEMENT)).thenReturn(management);
    when(management.getId()).thenReturn(MANAGEMENT);
    when(management.isEnabled()).thenReturn(true);
    when(management.getServiceAccountClientLink()).thenReturn(MANAGEMENT_CLIENT);
    when(managementClient.getId()).thenReturn(MANAGEMENT_CLIENT);
    when(managementClient.getClientId()).thenReturn("association-reader");
    when(managementClient.isEnabled()).thenReturn(true);
    when(managementClient.isServiceAccountsEnabled()).thenReturn(true);
    when(realm.getClientByClientId("association-reader")).thenReturn(managementClient);
    when(session.getProvider(SignatureProvider.class, "RS256")).thenReturn(signature);
    KeyWrapper wrapper = new KeyWrapper();
    wrapper.setPublicKey(key.getPublic());
    wrapper.setAlgorithm("RS256");
    wrapper.setKid("fixture-key");
    when(signature.verifier("fixture-key"))
        .thenAnswer(
            a -> {
              signatureChecks++;
              return new AsymmetricSignatureVerifierContext(wrapper);
            });
    when(session.getProvider(DatastoreProvider.class)).thenReturn(datastore);
    when(datastore.userLocalStorage()).thenReturn(local);
    when(realm.getClientById(CLIENT))
        .thenAnswer(
            a -> {
              targetReads++;
              return client;
            });
    when(client.getId()).thenReturn(CLIENT);
    when(client.getClientId()).thenReturn("ticket-reader");
    when(client.isEnabled()).thenReturn(true);
    when(client.isServiceAccountsEnabled()).thenReturn(true);
    when(local.getUserById(realm, SUBJECT)).thenReturn(user);
    when(local.getServiceAccount(client)).thenReturn(user);
    when(user.getId()).thenReturn(SUBJECT);
    when(user.getServiceAccountClientLink()).thenReturn(CLIENT);
    when(user.isEnabled()).thenReturn(true);
    grant =
        new LinkedHashMap<>(
            Map.of(
                "issuer",
                ISSUER,
                "realm_id",
                REALM,
                "iam_audience",
                "review-client",
                "management_client_id",
                "association-reader",
                "management_subject_id",
                MANAGEMENT,
                "client_uuid",
                CLIENT,
                "client_id",
                "ticket-reader",
                "subject_id",
                SUBJECT,
                "tenant_id",
                TENANT));
    resource = new AssociationResource(session, registry(true));
    long now = Instant.now().getEpochSecond();
    claims =
        Grants.JSON.valueToTree(
            Map.ofEntries(
                Map.entry("iss", ISSUER),
                Map.entry("sub", MANAGEMENT),
                Map.entry("azp", "association-reader"),
                Map.entry("aud", List.of("review-client", AssociationResource.AUDIENCE)),
                Map.entry("typ", "Bearer"),
                Map.entry("iat", now - 1),
                Map.entry("exp", now + 29),
                Map.entry("jti", UUID.randomUUID().toString()),
                Map.entry("tenant_id", TENANT),
                Map.entry("sg_principal_type", "workload"),
                Map.entry("sg_identity_contract", AssociationResource.CONTRACT),
                Map.entry("sg_permissions", List.of(AssociationResource.PERMISSION)),
                Map.entry(
                    "sg_registration_target",
                    Map.of(
                        "issuer",
                        ISSUER,
                        "client_uuid",
                        CLIENT,
                        "client_id",
                        "ticket-reader",
                        "subject_id",
                        SUBJECT,
                        "tenant_id",
                        TENANT))));
  }

  Grants registry(boolean enabled) throws Exception {
    return new Grants(
        enabled, Grants.JSON.writeValueAsString(Map.of("version", 1, "grants", List.of(grant))));
  }

  String signed(String json, KeyPair pair) throws Exception {
    String h =
        Base64.getUrlEncoder()
            .withoutPadding()
            .encodeToString(
                "{\"alg\":\"RS256\",\"typ\":\"JWT\",\"kid\":\"fixture-key\"}"
                    .getBytes(StandardCharsets.UTF_8));
    String p =
        Base64.getUrlEncoder()
            .withoutPadding()
            .encodeToString(json.getBytes(StandardCharsets.UTF_8));
    Signature signer = Signature.getInstance("SHA256withRSA");
    signer.initSign(pair.getPrivate());
    signer.update((h + "." + p).getBytes(StandardCharsets.US_ASCII));
    return h
        + "."
        + p
        + "."
        + Base64.getUrlEncoder().withoutPadding().encodeToString(signer.sign());
  }

  Response read() throws Exception {
    incoming.put("Authorization", List.of("Bearer " + signed(claims.toString(), key)));
    return resource.read(CLIENT, body);
  }

  void deny(Response r) {
    assertEquals(503, r.getStatus());
    assertEquals(Map.of("detail", "Association observation unavailable"), r.getEntity());
    assertEquals("no-store", r.getHeaderString("Cache-Control"));
  }

  void noTarget() {
    assertEquals(0, targetReads);
    verify(local, never()).getUserById(any(), any());
    verify(local, never()).getServiceAccount(any());
  }

  @AfterEach
  void noUnqualifiedEffects() {
    verify(session, never()).sessions();
    verify(nativeUsers, never()).getUserByUsername(any(), any());
    for (Object mock : mocks)
      for (var call : mockingDetails(mock).getInvocations()) {
        String n = call.getMethod().getName();
        assertFalse(
            n.matches(
                "^(add|remove|delete|create|update|grant|revoke|persist|merge|flush|enable).*"),
            "No provider write helpers: " + n);
      }
  }

  @Test
  void nativeHostnameRootCanHaveEmptyBasePath() throws Exception {
    when(uri.getBaseUri()).thenReturn(URI.create("https://identity.internal.test"));
    assertEquals(200, read().getStatus());
  }

  @Test
  void nativeClientIdMustMatchAuthorizedParty() throws Exception {
    claims.put("client_id", "association-reader");
    assertEquals(200, read().getStatus());
    assertEquals(1, signatureChecks);
  }

  @Test
  void nativeRSAAndExactAssociationProduceMinimalObservation() throws Exception {
    Response r = read();
    assertEquals(200, r.getStatus());
    assertEquals(1, signatureChecks);
    assertEquals(2, targetReads);
    Map<?, ?> v = (Map<?, ?>) r.getEntity();
    assertEquals(
        Set.of(
            "contract",
            "issuer",
            "realm_id",
            "client_uuid",
            "client_id",
            "subject_id",
            "tenant_id",
            "client_enabled",
            "subject_enabled",
            "observed_at"),
        v.keySet());
    assertEquals(TENANT, v.get("tenant_id"));
    assertEquals(CLIENT, v.get("client_uuid"));
    assertEquals(SUBJECT, v.get("subject_id"));
    assertEquals("no-store", r.getHeaderString("Cache-Control"));
  }

  @Test
  void disabledStateIsObservedWithoutEnablingIt() throws Exception {
    when(client.isEnabled()).thenReturn(false);
    when(user.isEnabled()).thenReturn(false);
    Response r = read();
    assertEquals(200, r.getStatus());
    assertEquals(false, ((Map<?, ?>) r.getEntity()).get("client_enabled"));
    assertEquals(false, ((Map<?, ?>) r.getEntity()).get("subject_enabled"));
  }

  @Test
  void factoryDiscoveryAndEmptyGrantsAdmitNothing() throws Exception {
    resource = (AssociationResource) new AssociationProviderFactory().create(session).getResource();
    deny(read());
    noTarget();
    assertEquals(0, signatureChecks);
  }

  @Test
  void explicitlyDisabledRegistryAdmitsNothing() throws Exception {
    resource = new AssociationResource(session, registry(false));
    deny(read());
    noTarget();
    assertEquals(0, signatureChecks);
  }

  @Test
  void forgedSignatureGoesThroughNativeVerifierAndDeniesBeforeTarget() throws Exception {
    incoming.put("Authorization", List.of("Bearer " + signed(claims.toString(), other)));
    deny(resource.read(CLIENT, body));
    noTarget();
    assertEquals(1, signatureChecks);
  }

  @Test
  void nativeRevocationIsCheckedBeforeTarget() throws Exception {
    when(revoked.contains(anyString())).thenReturn(true);
    deny(read());
    noTarget();
  }

  @Test
  void disabledNativeManagementClientDeniesBeforeTarget() throws Exception {
    when(managementClient.isEnabled()).thenReturn(false);
    deny(read());
    noTarget();
  }

  @Test
  void missingNativeManagementSubjectDeniesWithoutUsernameFallback() throws Exception {
    when(nativeUsers.getUserById(realm, MANAGEMENT)).thenReturn(null);
    deny(read());
    noTarget();
  }

  @Test
  void nonServiceAccountManagementIdentityDeniesBeforeTarget() throws Exception {
    when(management.getServiceAccountClientLink()).thenReturn(null);
    deny(read());
    noTarget();
  }

  static Stream<Arguments> badClaims() {
    return Stream.of(
        Arguments.of("iss", "https://foreign.test/realms/synthetic"),
        Arguments.of("sub", FOREIGN),
        Arguments.of("azp", "foreign"),
        Arguments.of("tenant_id", FOREIGN),
        Arguments.of("typ", "ID"),
        Arguments.of("sg_principal_type", "user"),
        Arguments.of("sg_identity_contract", "keycloak-workload-read-v1"),
        Arguments.of("sg_permissions", List.of("iam.manage_workload_association")),
        Arguments.of("aud", List.of("review-client")),
        Arguments.of("aud", List.of("review-client", AssociationResource.AUDIENCE, "account")),
        Arguments.of("aud", List.of(AssociationResource.AUDIENCE, AssociationResource.AUDIENCE)),
        Arguments.of("jti", "alias"),
        Arguments.of("exp", 1),
        Arguments.of("iat", 1),
        Arguments.of("scope", "offline_access"),
        Arguments.of("realm_access", Map.of("roles", List.of("admin"))),
        Arguments.of(
            "resource_access", Map.of("realm-management", Map.of("roles", List.of("view-users")))),
        Arguments.of("sg_registration_target", Map.of()),
        Arguments.of("sid", "session"),
        Arguments.of("session_state", "session"),
        Arguments.of("preferred_username", "fallback"),
        Arguments.of("act", Map.of("sub", SUBJECT)),
        Arguments.of("may_act", Map.of()),
        Arguments.of("sg_actor", Map.of()),
        Arguments.of("client_id", "alias"),
        Arguments.of("exp", true));
  }

  @ParameterizedTest
  @MethodSource("badClaims")
  void signedWrongAuthorityDeniesBeforeTarget(String name, Object value) throws Exception {
    claims.set(name, Grants.JSON.valueToTree(value));
    deny(read());
    noTarget();
  }

  @ParameterizedTest
  @ValueSource(
      strings = {
        "future_iat",
        "long_life",
        "future_nbf",
        "expired",
        "null_target",
        "foreign_target",
        "missing_permission",
        "float_time"
      })
  void timeAndTargetAmbiguityDenies(String kind) throws Exception {
    long now = Instant.now().getEpochSecond();
    switch (kind) {
      case "future_iat" -> claims.put("iat", now + 10);
      case "long_life" -> claims.put("exp", now + 100);
      case "future_nbf" -> claims.put("nbf", now + 10);
      case "expired" -> claims.put("exp", now - 1);
      case "null_target" -> claims.putNull("sg_registration_target");
      case "foreign_target" ->
          ((ObjectNode) claims.get("sg_registration_target")).put("tenant_id", FOREIGN);
      case "missing_permission" -> claims.remove("sg_permissions");
      case "float_time" -> claims.put("iat", now - 0.5);
    }
    deny(read());
    noTarget();
  }

  @ParameterizedTest
  @ValueSource(
      strings = {
        "cookie",
        "query",
        "empty_query",
        "path_alias",
        "encoded_uuid",
        "post",
        "head",
        "http",
        "body",
        "chunked",
        "tenant_header",
        "duplicate_bearer",
        "lowercase_bearer",
        "foreign_host",
        "unannounced_body",
        "empty_length"
      })
  void requestAmbiguityDeniesBeforeAuthentication(String kind) throws Exception {
    incoming.put("Authorization", List.of("Bearer " + signed(claims.toString(), key)));
    URI path = uri.getRequestUri();
    switch (kind) {
      case "cookie" -> incoming.put("Cookie", List.of("session=synthetic"));
      case "query" ->
          when(uri.getRequestUri()).thenReturn(URI.create(path + "?tenant_id=" + TENANT));
      case "empty_query" -> when(uri.getRequestUri()).thenReturn(URI.create(path + "?"));
      case "path_alias" -> when(uri.getRequestUri()).thenReturn(URI.create(path + "/"));
      case "encoded_uuid" ->
          when(uri.getRequestUri())
              .thenReturn(URI.create(path.toString().replace(CLIENT, "%33" + CLIENT.substring(1))));
      case "post" -> when(request.getHttpMethod()).thenReturn("POST");
      case "head" -> when(request.getHttpMethod()).thenReturn("HEAD");
      case "foreign_host" ->
          when(uri.getRequestUri())
              .thenReturn(
                  URI.create(
                      path.toString().replace("identity.internal.test", "foreign.internal.test")));
      case "http" ->
          when(uri.getRequestUri())
              .thenReturn(URI.create(path.toString().replace("https:", "http:")));
      case "body" -> incoming.put("Content-Length", List.of("2"));
      case "unannounced_body" -> body = new java.io.ByteArrayInputStream(new byte[] {1});
      case "empty_length" -> incoming.put("Content-Length", List.of(""));
      case "chunked" -> incoming.put("Transfer-Encoding", List.of("chunked"));
      case "tenant_header" -> incoming.put("x-tenant-id", List.of(TENANT));
      case "duplicate_bearer" -> incoming.put("Authorization", List.of("Bearer a", "Bearer b"));
      case "lowercase_bearer" -> incoming.put("Authorization", List.of("bearer a"));
    }
    deny(resource.read(CLIENT, body));
    noTarget();
    assertEquals(0, signatureChecks);
  }

  @ParameterizedTest
  @ValueSource(
      strings = {
        "missing_client",
        "missing_subject",
        "wrong_link",
        "wrong_client_id",
        "wrong_subject_id",
        "missing_reciprocal",
        "foreign_reciprocal",
        "federation",
        "service_flag",
        "outage",
        "rebound_during_read",
        "nonlocal",
        "changed_enabled_second_lookup",
        "reciprocal_state_conflict"
      })
  void modelDriftAndMissingStateCannotBeRepaired(String kind) throws Exception {
    switch (kind) {
      case "missing_client" -> when(realm.getClientById(CLIENT)).thenReturn(null);
      case "missing_subject" -> when(local.getUserById(realm, SUBJECT)).thenReturn(null);
      case "wrong_link" -> when(user.getServiceAccountClientLink()).thenReturn(FOREIGN);
      case "wrong_client_id" -> when(client.getClientId()).thenReturn("foreign");
      case "wrong_subject_id" -> when(user.getId()).thenReturn(FOREIGN);
      case "missing_reciprocal" -> when(local.getServiceAccount(client)).thenReturn(null);
      case "foreign_reciprocal" -> when(local.getServiceAccount(client)).thenReturn(management);
      case "federation" -> when(user.getFederationLink()).thenReturn(FOREIGN);
      case "service_flag" -> when(client.isServiceAccountsEnabled()).thenReturn(false);
      case "outage" ->
          when(local.getUserById(realm, SUBJECT))
              .thenThrow(new IllegalStateException("synthetic-private-diagnostic"));
      case "rebound_during_read" ->
          when(local.getServiceAccount(client)).thenReturn(user, management);
      case "nonlocal" -> when(datastore.userLocalStorage()).thenReturn(nativeUsers);
      case "changed_enabled_second_lookup" -> {
        ClientModel changed = sdk(ClientModel.class);
        when(changed.getId()).thenReturn(CLIENT);
        when(changed.getClientId()).thenReturn("ticket-reader");
        when(changed.isServiceAccountsEnabled()).thenReturn(true);
        when(local.getServiceAccount(changed)).thenReturn(user);
        when(realm.getClientById(CLIENT)).thenReturn(client, changed);
      }
      case "reciprocal_state_conflict" -> {
        UserModel changed = sdk(UserModel.class);
        when(changed.getId()).thenReturn(SUBJECT);
        when(changed.getServiceAccountClientLink()).thenReturn(CLIENT);
        when(local.getServiceAccount(client)).thenReturn(changed);
      }
    }
    deny(read());
    assertEquals(1, signatureChecks);
  }

  @ParameterizedTest
  @ValueSource(strings = {"duplicate", "trailing", "oversized", "malformed"})
  void ambiguousOrUnboundedJWTClaimsDenyBeforeNativeAuth(String kind) throws Exception {
    String payload = claims.toString();
    switch (kind) {
      case "duplicate" ->
          payload =
              payload.substring(0, payload.length() - 1) + ",\"tenant_id\":\"" + TENANT + "\"}";
      case "trailing" -> payload = payload + " {}";
      case "oversized" -> payload = "{\"padding\":\"" + "x".repeat(33000) + "\"}";
      case "malformed" -> payload = "[]";
    }
    incoming.put("Authorization", List.of("Bearer " + signed(payload, key)));
    deny(resource.read(CLIENT, body));
    noTarget();
    assertEquals(0, signatureChecks);
  }

  @ParameterizedTest
  @ValueSource(
      strings = {
        "duplicate",
        "trailing",
        "unknown",
        "conflicting",
        "nonuuid",
        "same_identity",
        "http",
        "version_type"
      })
  void invalidOwnedGrantsDenyConfiguration(String kind) throws Exception {
    Map<String, Object> root = new LinkedHashMap<>(Map.of("version", 1, "grants", List.of(grant)));
    switch (kind) {
      case "unknown" -> grant.put("approved", true);
      case "conflicting" -> root.put("grants", List.of(grant, grant));
      case "nonuuid" -> grant.put("tenant_id", "alias");
      case "same_identity" -> grant.put("management_subject_id", SUBJECT);
      case "http" -> grant.put("issuer", ISSUER.replace("https:", "http:"));
      case "version_type" -> root.put("version", true);
    }
    String json = Grants.JSON.writeValueAsString(root);
    if (kind.equals("duplicate")) json = "{\"version\":1,\"version\":2,\"grants\":[]}";
    if (kind.equals("trailing")) json += " {}";
    String input = json;
    assertThrows(IllegalArgumentException.class, () -> new Grants(true, input));
  }

  @Test
  void immutableGrantRowsHaveRevisionAndHashButAreNotReturned() throws Exception {
    Grants g = registry(true);
    assertEquals(1, g.version);
    assertEquals(64, g.sha256.length());
    assertThrows(UnsupportedOperationException.class, () -> g.rows.clear());
    assertEquals(200, read().getStatus());
  }
}
