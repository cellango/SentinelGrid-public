/* SPDX-License-Identifier: Apache-2.0 */
package ai.sentinelgrid.research;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static ai.sentinelgrid.research.EntryGuardProbe.State.*;

import java.net.URI;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;
import jakarta.ws.rs.WebApplicationException;
import jakarta.ws.rs.core.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.*;
import org.keycloak.authentication.*;
import org.keycloak.authentication.authenticators.client.ClientIdAndSecretAuthenticator;
import org.keycloak.common.ClientConnection;
import org.keycloak.events.*;
import org.keycloak.http.HttpRequest;
import org.keycloak.http.HttpResponse;
import org.keycloak.models.*;
import org.keycloak.protocol.oidc.endpoints.TokenEndpoint;
import org.keycloak.protocol.oidc.grants.*;
import org.keycloak.services.cors.*;
import org.keycloak.utils.KeycloakSessionUtil;
import org.keycloak.vault.*;

/** Real native endpoint/authenticator/grant; doubles only at storage/context boundaries. */
class NativeEntryGuardTest {
    static final String REALM = "8f2ca36a-12d4-4bb4-96db-26b755e30b1b";
    static final boolean GUARDED = Boolean.getBoolean("entryGuard.guarded");
    @BeforeAll static void nativeFeatureProfile() { org.keycloak.common.Profile.defaults(); }
    @AfterAll static void resetFeatureProfile() { org.keycloak.common.Profile.reset(); }
    KeycloakSession previous;
    @AfterEach void restoreThreadContext() { KeycloakSessionUtil.setKeycloakSession(previous); }

    static Stream<String> grantIds() {
        List<String> ids = ServiceLoader.load(OAuth2GrantTypeFactory.class).stream()
            .map(p -> p.get().getId()).sorted().toList();
        assertEquals(10, ids.size(), "Pinned factory set changed; review coverage");
        assertEquals(10, new HashSet<>(ids).size());
        return ids.stream();
    }
    static Stream<Arguments> deniedEntries() {
        List<String> ids = new ArrayList<>(grantIds().toList());
        ids.add("unknown-fixture-grant"); ids.add(null);
        return ids.stream().flatMap(id -> Stream.of(ENROLLED_CLOSED, UNKNOWN)
            .map(state -> Arguments.of(id, state)));
    }

    static final class PreprocessReached extends RuntimeException {}
    static class Fixture {
        final KeycloakSession session = mock(KeycloakSession.class);
        final KeycloakContext context = mock(KeycloakContext.class);
        final RealmModel realm = mock(RealmModel.class);
        final HttpRequest request = mock(HttpRequest.class);
        final HttpResponse response = mock(HttpResponse.class);
        final HttpHeaders headers = mock(HttpHeaders.class);
        final ClientConnection connection = mock(ClientConnection.class);
        final EventBuilder event = mock(EventBuilder.class, RETURNS_SELF);
        final MultivaluedMap<String,String> form = new MultivaluedHashMap<>();
        final MultivaluedMap<String,String> headerValues = new MultivaluedHashMap<>();
        final TokenEndpoint endpoint;
        Fixture(String grant) {
            when(session.getContext()).thenReturn(context);
            when(session.getTransactionManager()).thenReturn(mock(KeycloakTransactionManager.class));
            when(context.getRealm()).thenReturn(realm);
            when(context.getConnection()).thenReturn(connection);
            when(context.getHttpRequest()).thenReturn(request);
            when(context.getHttpResponse()).thenReturn(response);
            when(context.getRequestHeaders()).thenReturn(headers);
            when(request.getHttpHeaders()).thenReturn(headers);
            when(request.getDecodedFormParameters()).thenReturn(form);
            when(headers.getRequestHeaders()).thenReturn(headerValues);
            when(headers.getMediaType()).thenReturn(MediaType.APPLICATION_FORM_URLENCODED_TYPE);
            when(realm.getId()).thenReturn(REALM);
            when(realm.getName()).thenReturn("fixture");
            when(realm.isEnabled()).thenReturn(true);
            org.keycloak.models.KeycloakUriInfo uri = mock(org.keycloak.models.KeycloakUriInfo.class);
            when(context.getUri()).thenReturn(uri);
            when(uri.getBaseUri()).thenReturn(URI.create("https://issuer.invalid/"));
            when(uri.getRequestUri()).thenReturn(URI.create("https://issuer.invalid/realms/fixture/protocol/openid-connect/token"));
            DefaultCorsFactory factory = new DefaultCorsFactory();
            factory.init(mock(org.keycloak.Config.Scope.class));
            when(session.getProvider(Cors.class)).thenAnswer(i -> factory.create(session));
            if (grant != null) form.putSingle("grant_type", grant);
            endpoint = new TokenEndpoint(session, null, event);
            clearInvocations(session, context, realm, request, response, headers, connection, event);
        }
        OAuth2GrantType sentinel(String id) throws Exception {
            OAuth2GrantType grant = mock(OAuth2GrantType.class);
            when(grant.getEventType()).thenReturn(EventType.CLIENT_LOGIN);
            doThrow(new PreprocessReached()).when(grant).preProcess(eq(session), any());
            when(session.getProvider(OAuth2GrantType.class, id)).thenReturn(grant);
            return grant;
        }
    }
    Fixture fixture(String id) {
        Fixture f = new Fixture(id);
        previous = KeycloakSessionUtil.setKeycloakSession(f.session);
        return f;
    }

    @Test void compiledNativeSourceOverlayIsLoaded() {
        assertTrue(TokenEndpoint.class.getProtectionDomain().getCodeSource().getLocation()
            .getPath().endsWith("/target/classes/"), "Dependency JAR cannot substitute for source overlay");
    }
    @ParameterizedTest @MethodSource("deniedEntries")
    void enrolledAndUnknownDenyBeforeAnyGrantOrRequestRead(String id, EntryGuardProbe.State state) throws Exception {
        Fixture f = fixture(id);
        OAuth2GrantType sentinel = id == null ? null : f.sentinel(id);
        // Caller-supplied enrollment/tenant hints cannot establish unmanaged control.
        f.form.putSingle("enrollment", "UNMANAGED_NATIVE_CONTROL");
        f.form.putSingle("tenant_id", REALM);
        f.headerValues.putSingle("X-Enrollment", "UNMANAGED_NATIVE_CONTROL");
        clearInvocations(f.session);
        try (var ignored = EntryGuardProbe.fixture(Map.of(REALM, state))) {
            if (GUARDED) {
                assertThrows(EntryGuardProbe.EntryDenied.class, f.endpoint::processGrantRequest);
                verifyNoInteractions(f.request, f.response, f.headers, f.connection, f.event, f.session);
                if (sentinel != null) verify(sentinel, never()).preProcess(any(), any());
            } else if (id != null) {
                assertThrows(PreprocessReached.class, f.endpoint::processGrantRequest);
                verify(sentinel).preProcess(eq(f.session), any());
            } else {
                assertThrows(WebApplicationException.class, f.endpoint::processGrantRequest);
            }
        }
    }
    @Test void absentEnrollmentAndWrongRealmFailClosed() throws Exception {
        Fixture f = fixture("client_credentials"); f.sentinel("client_credentials");
        if (GUARDED) assertThrows(EntryGuardProbe.EntryDenied.class, f.endpoint::processGrantRequest);
        else assertThrows(PreprocessReached.class, f.endpoint::processGrantRequest);
        try (var ignored = EntryGuardProbe.fixture(Map.of("another-realm", UNMANAGED_NATIVE_CONTROL))) {
            assertThrows(EntryGuardProbe.EntryDenied.class, () -> EntryGuardProbe.beforeNativeDispatch(f.realm));
        }
        assertThrows(EntryGuardProbe.EntryDenied.class, () -> EntryGuardProbe.beforeNativeDispatch(null));
    }
    @Test void testOwnerFixtureDoesNotEscapeScopeOrThread() throws Exception {
        Fixture f = fixture("client_credentials");
        try (var ignored = EntryGuardProbe.fixture(Map.of(REALM, UNMANAGED_NATIVE_CONTROL))) {
            assertDoesNotThrow(() -> EntryGuardProbe.beforeNativeDispatch(f.realm));
            assertThrows(IllegalStateException.class, () -> EntryGuardProbe.fixture(Map.of()));
            try (ExecutorService executor = Executors.newSingleThreadExecutor()) {
                assertTrue(executor.submit(() -> {
                    try { EntryGuardProbe.beforeNativeDispatch(f.realm); return false; }
                    catch (EntryGuardProbe.EntryDenied expected) { return true; }
                }).get(5, TimeUnit.SECONDS));
            }
        }
        assertThrows(EntryGuardProbe.EntryDenied.class, () -> EntryGuardProbe.beforeNativeDispatch(f.realm));
    }
    @ParameterizedTest @ValueSource(strings={"valid", "wrong", "missing", "expired", "disabled", "unknown", "missing-account"})
    void unmanagedControlPreservesActualNativeClientAuthentication(String scenario) throws Exception {
        Fixture f = fixture("client_credentials");
        ClientModel client = mock(ClientModel.class);
        ClientProvider clients = mock(ClientProvider.class);
        UserProvider users = mock(UserProvider.class);
        when(f.session.clients()).thenReturn(clients);
        when(f.session.users()).thenReturn(users);
        when(clients.getClientByClientId(f.realm, "fixture-client"))
            .thenReturn(scenario.equals("unknown") ? null : client);
        when(client.getClientId()).thenReturn("fixture-client");
        when(client.getId()).thenReturn("fixture-client-model");
        when(client.isEnabled()).thenReturn(!scenario.equals("disabled"));
        when(client.getProtocol()).thenReturn("openid-connect");
        when(client.getClientAuthenticatorType()).thenReturn("client-secret");
        when(client.getAttributes()).thenReturn(Map.of());
        when(client.getWebOrigins()).thenReturn(Set.of());
        when(f.context.getClient()).thenReturn(client);
        // Ephemeral synthetic input; never a workload credential or token.
        String secret = UUID.randomUUID().toString();
        when(client.getSecret()).thenReturn(secret);
        when(client.isServiceAccountsEnabled()).thenReturn(scenario.equals("missing-account"));
        org.keycloak.Config.Scope config = mock(org.keycloak.Config.Scope.class, invocation ->
            invocation.getArguments().length == 2 ? invocation.getArgument(1) :
                (invocation.getMethod().getReturnType().isPrimitive() ? RETURNS_DEFAULTS.answer(invocation) : null));
        var protocol = new org.keycloak.protocol.oidc.OIDCLoginProtocol(new org.keycloak.protocol.oidc.OIDCProviderConfig(config));
        when(f.session.getProvider(org.keycloak.protocol.LoginProtocol.class, "openid-connect")).thenReturn(protocol);
        if (scenario.equals("expired")) when(client.getAttribute("client.secret.expiration.time")).thenReturn("1");
        VaultTranscriber vault = mock(VaultTranscriber.class);
        VaultStringSecret value = mock(VaultStringSecret.class);
        when(value.get()).thenReturn(Optional.empty());
        when(vault.getStringSecret(anyString())).thenReturn(value);
        when(f.session.vault()).thenReturn(vault);
        AuthenticationFlowModel flow = new AuthenticationFlowModel();
        flow.setId("fixture-flow"); flow.setProviderId(AuthenticationFlow.CLIENT_FLOW);
        AuthenticationExecutionModel execution = new AuthenticationExecutionModel();
        execution.setId("fixture-execution"); execution.setAuthenticator("client-secret");
        execution.setRequirement(AuthenticationExecutionModel.Requirement.REQUIRED);
        when(f.realm.getClientAuthenticationFlow()).thenReturn(flow);
        when(f.realm.getAuthenticationFlowById(flow.getId())).thenReturn(flow);
        when(f.realm.getAuthenticationExecutionsStream(flow.getId())).thenAnswer(i -> Stream.of(execution));
        KeycloakSessionFactory sessionFactory = mock(KeycloakSessionFactory.class);
        when(f.session.getKeycloakSessionFactory()).thenReturn(sessionFactory);
        when(sessionFactory.getProviderFactory(ClientAuthenticator.class, "client-secret"))
            .thenReturn(new ClientIdAndSecretAuthenticator());
        when(f.session.getProvider(OAuth2GrantType.class, "client_credentials"))
            .thenReturn(new ClientCredentialsGrantType());
        f.form.putSingle("client_id", "fixture-client");
        if (!scenario.equals("missing")) f.form.putSingle("client_secret", scenario.equals("wrong") ? UUID.randomUUID().toString() : secret);
        try (var ignored = EntryGuardProbe.fixture(Map.of(REALM, UNMANAGED_NATIVE_CONTROL))) {
            WebApplicationException failure = assertThrows(WebApplicationException.class, f.endpoint::processGrantRequest);
            assertEquals(401, failure.getResponse().getStatus(), "Unexpected fixture failure, not native denial");
            org.keycloak.representations.idm.OAuth2ErrorRepresentation error =
                (org.keycloak.representations.idm.OAuth2ErrorRepresentation) failure.getResponse().getEntity();
            assertEquals(scenario.equals("missing-account") ? "invalid_request" :
                ((scenario.equals("disabled") || scenario.equals("unknown")) ? "invalid_client" : "unauthorized_client"), error.getError());
            if (scenario.equals("valid")) {
                assertEquals("Client not enabled to retrieve service account", error.getErrorDescription());
                verify(client).isServiceAccountsEnabled();
            } else if (scenario.equals("missing-account")) {
                assertEquals("The associated service account for the client does not exist", error.getErrorDescription());
                verify(users).getServiceAccount(client);
                verifyNoMoreInteractions(users);
            } else verify(client, never()).isServiceAccountsEnabled();
            if (!scenario.equals("missing-account")) verifyNoInteractions(users);
            verify(f.session, never()).authenticationSessions();
            verify(f.session, never()).sessions();
        }
    }
}
