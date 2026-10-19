/* SPDX-License-Identifier: Apache-2.0 */
package org.keycloak.services.resources;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import static ai.sentinelgrid.research.RealmEntryProbe.State.*;

import ai.sentinelgrid.research.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.container.*;
import jakarta.ws.rs.core.*;
import org.jboss.logging.Logger;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.*;
import org.keycloak.models.*;
import org.keycloak.provider.Provider;
import org.keycloak.services.*;
import org.keycloak.services.error.KeycloakErrorHandler;
import org.keycloak.tracing.*;
import org.keycloak.utils.KeycloakSessionUtil;
import org.keycloak.quarkus.runtime.integration.jaxrs.CloseSessionFilter;

/** Native resolver/manager/transaction/session/error/close code with model and HTTP doubles. */
class RealmEntryTest {
    static final String HINT = "synthetic-realm";
    static final boolean GUARDED = Boolean.getBoolean("realmEntry.guarded");
    final List<NativeSession> owned = new ArrayList<>();
    @BeforeAll static void configureNativeProfile() { org.keycloak.common.Profile.defaults(); }
    @AfterAll static void resetNativeProfile() { org.keycloak.common.Profile.reset(); }
    @AfterEach void cleanup() {
        for (NativeSession session : owned) if (!session.isClosed()) {
            session.getTransactionManager().setRollbackOnly();
            try { session.close(); } catch (RuntimeException ignored) { /* tested fault */ }
        }
        KeycloakSessionUtil.setKeycloakSession(null);
    }
    static final class LookupReached extends RuntimeException {}
    static final class TrackingTx extends AbstractKeycloakTransaction {
        int commits; int rollbacks; boolean failRollback;
        protected void commitImpl() { commits++; }
        protected void rollbackImpl() { rollbacks++; if (failRollback) throw new IllegalStateException("Synthetic rollback failure"); }
    }
    static final class NativeSession extends DefaultKeycloakSession {
        final RealmProvider models = mock(RealmProvider.class);
        int realmAccess; int otherProviderAccess;
        final NoopTracingProvider tracing = new NoopTracingProvider();
        NativeSession() { super(mock(DefaultKeycloakSessionFactory.class)); }
        protected DefaultKeycloakContext createKeycloakContext(KeycloakSession session) {
            return mock(DefaultKeycloakContext.class);
        }
        public RealmProvider realms() { realmAccess++; return models; }
        public <T extends Provider> T getProvider(Class<T> type) {
            if (type == TracingProvider.class) return type.cast(tracing);
            otherProviderAccess++; throw new AssertionError("Unexpected provider construction");
        }
        public <T extends Provider> T getProvider(Class<T> type, String id) {
            otherProviderAccess++; throw new AssertionError("Unexpected named provider construction");
        }
    }
    NativeSession session() {
        NativeSession s = new NativeSession(); owned.add(s);
        when(s.models.getRealmByName(anyString())).thenThrow(new LookupReached());
        return s;
    }
    RealmsResource resource(KeycloakSession session) { RealmsResource r = new RealmsResource(); r.session = session; return r; }
    static Stream<String> routes() {
        return Stream.of("oidc", "saml", "unknown-protocol", "login", "broker", "registration",
            "management", "account", "public-realm", "redirect", "authorization", "extension", "discovery");
    }
    static Stream<Arguments> deniedRoutes() {
        return routes().flatMap(route -> Stream.of(ENROLLED_CLOSED, UNKNOWN, AMBIGUOUS, LOOKUP_ERROR, INCARNATION_MISMATCH)
            .map(state -> Arguments.of(route, state)));
    }
    Object invoke(String route, RealmsResource r) {
        return switch (route) {
            case "oidc" -> r.getProtocol(HINT, "openid-connect");
            case "saml" -> r.getProtocol(HINT, "saml");
            case "unknown-protocol" -> r.getProtocol(HINT, "unknown-fixture-protocol");
            case "login" -> r.getLoginActionsService(HINT);
            case "broker" -> r.getBrokerService(HINT);
            case "registration" -> r.getClientsService(HINT);
            case "management" -> r.getClientsManagementService(HINT);
            case "account" -> r.getAccountService(HINT);
            case "public-realm" -> r.getRealmResource(HINT);
            case "redirect" -> r.getRedirect(HINT, "fixture-client");
            case "authorization" -> r.getAuthorizationService(HINT);
            case "extension" -> r.resolveRealmExtension(HINT, "unknown-fixture-extension");
            case "discovery" -> r.getWellKnown(HINT, "openid-configuration");
            default -> throw new IllegalArgumentException(route);
        };
    }
    @Test void exactNativeOverlayClassesAreLoaded() {
        for (Class<?> type : List.of(RealmsResource.class, KeycloakErrorHandler.class, CloseSessionFilter.class))
            assertTrue(type.getProtectionDomain().getCodeSource().getLocation().getPath().endsWith("/target/classes/"));
        assertFalse(mockingDetails(new NativeSession()).isMock());
    }
    @ParameterizedTest @MethodSource("deniedRoutes")
    void denyBeforeNativeRealmLookupAndConstruction(String route, RealmEntryProbe.State state) throws Exception {
        NativeSession s = session(); RealmsResource r = resource(s);
        try (var ignored = RealmEntryProbe.fixture(s, HINT, state)) {
            if (GUARDED) {
                assertThrows(RealmEntryProbe.Denied.class, () -> invoke(route, r));
                assertEquals(0, s.realmAccess); assertEquals(0, s.otherProviderAccess);
                verifyNoInteractions(s.getContext(), s.models);
            } else {
                assertThrows(LookupReached.class, () -> invoke(route, r));
                assertEquals(1, s.realmAccess); verify(s.models).getRealmByName(HINT);
            }
        }
    }
    @ParameterizedTest @MethodSource("routes")
    void explicitUnmanagedControlReachesActualNativeRealmManager(String route) throws Exception {
        NativeSession s = session();
        try (var ignored = RealmEntryProbe.fixture(s, HINT, UNMANAGED_NATIVE_CONTROL)) {
            assertThrows(LookupReached.class, () -> invoke(route, resource(s)));
            assertEquals(1, s.realmAccess); verify(s.models).getRealmByName(HINT);
        }
    }
    @Test void nativeMissingRealmStillReturnsNativeNotFound() throws Exception {
        NativeSession s = session(); doReturn(null).when(s.models).getRealmByName(HINT);
        try (var ignored = RealmEntryProbe.fixture(s, HINT, UNMANAGED_NATIVE_CONTROL)) {
            NotFoundException failure = assertThrows(NotFoundException.class, () -> resource(s).getProtocol(HINT, "openid-connect"));
            assertEquals(404, failure.getResponse().getStatus());
            assertEquals("Realm does not exist", failure.getMessage());
        }
    }
    @Test void absentWrongHintWrongSessionAndNullInputsDeny() throws Exception {
        NativeSession s = session();
        assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
        try (var ignored = RealmEntryProbe.fixture(s, HINT, UNMANAGED_NATIVE_CONTROL)) {
            assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, "another-hint"));
            assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
        }
        try (var ignored = RealmEntryProbe.fixture(s, HINT, UNMANAGED_NATIVE_CONTROL)) {
            assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(session(), HINT));
        }
        try (var ignored = RealmEntryProbe.fixture(s, HINT, UNMANAGED_NATIVE_CONTROL)) {
            assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, null));
            assertThrows(IllegalStateException.class, () -> RealmEntryProbe.fixture(s, HINT, UNMANAGED_NATIVE_CONTROL));
        }
        assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(null, HINT));
    }
    @Test void unmanagedFixtureDoesNotCrossThreadOrOutliveScope() throws Exception {
        NativeSession s = session();
        try (var ignored = RealmEntryProbe.fixture(s, HINT, UNMANAGED_NATIVE_CONTROL);
             ExecutorService executor = Executors.newSingleThreadExecutor()) {
            assertDoesNotThrow(() -> RealmEntryProbe.beforeRealmResolution(s, HINT));
            assertTrue(executor.submit(() -> {
                try { RealmEntryProbe.beforeRealmResolution(s, HINT); return false; }
                catch (RealmEntryProbe.Denied expected) { return true; }
            }).get(5, TimeUnit.SECONDS));
        }
        assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
    }
    static void checkResponse(Response response) {
        assertEquals(503, response.getStatus());
        assertEquals(MediaType.APPLICATION_JSON_TYPE, response.getMediaType());
        assertEquals("no-store", response.getHeaderString("Cache-Control"));
        assertEquals("no-cache", response.getHeaderString("Pragma"));
        assertEquals("{\"error\":\"temporarily_unavailable\"}", response.getEntity());
    }
    @ParameterizedTest @ValueSource(booleans={false,true})
    void minimalMapperUsesNativeRollbackAndCloseWithoutContextRead(boolean active) throws Exception {
        NativeSession s = session(); TrackingTx tx = new TrackingTx();
        if (active) {
            s.getTransactionManager().setJTAPolicy(KeycloakTransactionManager.JTAPolicy.NOT_SUPPORTED);
            s.getTransactionManager().begin(); s.getTransactionManager().enlist(tx);
        }
        KeycloakSessionUtil.setKeycloakSession(s);
        try (var ignored = RealmEntryProbe.fixture(s, HINT, UNKNOWN)) {
            RealmEntryProbe.Denied denial = assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
            Response response = new MinimalDenialMapper().toResponse(denial); checkResponse(response);
            assertFalse(denial.cleanupFaultObserved()); assertTrue(s.isClosed()); assertNull(KeycloakSessionUtil.getKeycloakSession());
            assertEquals(0, tx.commits); assertEquals(active ? 1 : 0, tx.rollbacks);
            assertEquals(0, s.realmAccess); assertEquals(0, s.otherProviderAccess); verifyNoInteractions(s.getContext(), s.models);
            // Native close filter tolerates the already-closed session for an ordinary entity.
            CloseSessionFilter filter = new CloseSessionFilter();
            var field = CloseSessionFilter.class.getDeclaredField("session"); field.setAccessible(true); field.set(filter, s);
            ContainerResponseContext context = mock(ContainerResponseContext.class);
            when(context.getEntity()).thenReturn(response.getEntity());
            filter.filter(mock(ContainerRequestContext.class), context);
            checkResponse(new MinimalDenialMapper().toResponse(denial));
            assertEquals(0, tx.commits); assertEquals(active ? 1 : 0, tx.rollbacks);
        }
        assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
    }
    @Test void nativeRollbackCanSwallowParticipantFailureAndCleanupRemainsUnqualified() {
        NativeSession s = session(); TrackingTx tx = new TrackingTx(); tx.failRollback = true;
        s.getTransactionManager().setJTAPolicy(KeycloakTransactionManager.JTAPolicy.NOT_SUPPORTED);
        s.getTransactionManager().begin(); s.getTransactionManager().enlist(tx); KeycloakSessionUtil.setKeycloakSession(s);
        var denial = assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
        checkResponse(new MinimalDenialMapper().toResponse(denial));
        assertFalse(denial.cleanupFaultObserved(), "Native close did not propagate the participant failure");
        assertTrue(s.isClosed()); assertEquals(0, tx.commits); assertEquals(1, tx.rollbacks);
        assertEquals(AbstractKeycloakTransaction.TransactionState.STARTED, tx.getState(),
            "Participant rollback threw before completion; closed session does not prove rollback");
        assertNull(KeycloakSessionUtil.getKeycloakSession());
    }
    @Test void refusedRollbackMarkerMustNotFallThroughToNativeCommitOnClose() {
        KeycloakSession s = mock(KeycloakSession.class); KeycloakTransactionManager tx = mock(KeycloakTransactionManager.class);
        when(s.getTransactionManager()).thenReturn(tx); when(tx.isActive()).thenReturn(true);
        doThrow(new IllegalStateException("Synthetic marker failure")).when(tx).setRollbackOnly();
        KeycloakSessionUtil.setKeycloakSession(s);
        var denial = assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
        checkResponse(new MinimalDenialMapper().toResponse(denial));
        assertTrue(denial.cleanupFaultObserved()); verify(s, never()).close(); verify(tx, never()).commit();
        assertNull(KeycloakSessionUtil.getKeycloakSession());
        // Resource cleanup remains incomplete in this fault: no production qualification.
    }
    @Test void unmarkedNativeCloseReallyCommitsTheControlTransaction() {
        NativeSession s = session(); TrackingTx tx = new TrackingTx();
        s.getTransactionManager().setJTAPolicy(KeycloakTransactionManager.JTAPolicy.NOT_SUPPORTED);
        s.getTransactionManager().begin(); s.getTransactionManager().enlist(tx); s.close();
        assertEquals(1, tx.commits); assertEquals(0, tx.rollbacks); assertTrue(s.isClosed());
    }
    @ParameterizedTest @ValueSource(strings={"get-manager", "mark-refused", "close-throws", "is-closed-throws"})
    void lifecycleFaultsReturnClosedAuthorityAndReportIncompleteCleanup(String fault) {
        KeycloakSession s = mock(KeycloakSession.class); KeycloakTransactionManager tx = mock(KeycloakTransactionManager.class);
        when(s.getTransactionManager()).thenReturn(tx); when(tx.isActive()).thenReturn(true);
        when(tx.getRollbackOnly()).thenReturn(!fault.equals("mark-refused"));
        if (fault.equals("get-manager")) when(s.getTransactionManager()).thenThrow(new IllegalStateException("Synthetic manager failure"));
        if (fault.equals("close-throws")) doThrow(new IllegalStateException("Synthetic close failure")).when(s).close();
        if (fault.equals("is-closed-throws")) when(s.isClosed()).thenThrow(new IllegalStateException("Synthetic lifecycle failure"));
        KeycloakSessionUtil.setKeycloakSession(s);
        var denial = assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
        checkResponse(new MinimalDenialMapper().toResponse(denial));
        assertTrue(denial.cleanupFaultObserved()); assertNull(KeycloakSessionUtil.getKeycloakSession()); verify(tx, never()).commit();
        if (!fault.equals("close-throws")) verify(s, never()).close();
    }
    @Test void nullSessionHasTheSameMinimalResponse() {
        var denial = assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(null, null));
        checkResponse(new MinimalDenialMapper().toResponse(denial));
    }
    @Test void anotherThreadCannotConsumeTheMarkerOrCloseItsNativeSession() throws Exception {
        NativeSession s = session(); KeycloakSessionUtil.setKeycloakSession(s);
        var denial = assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
        try (ExecutorService executor = Executors.newSingleThreadExecutor()) {
            assertEquals(503, executor.submit(() -> new MinimalDenialMapper().toResponse(denial).getStatus()).get(5, TimeUnit.SECONDS));
        }
        assertFalse(s.isClosed()); assertSame(s, KeycloakSessionUtil.getKeycloakSession());
        checkResponse(new MinimalDenialMapper().toResponse(denial)); assertTrue(s.isClosed());
    }
    @Test void foreignThreadBindingIsNotClosedOrCleared() {
        NativeSession s = session(); NativeSession foreign = session(); KeycloakSessionUtil.setKeycloakSession(foreign);
        var denial = assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
        checkResponse(new MinimalDenialMapper().toResponse(denial));
        assertTrue(denial.cleanupFaultObserved()); assertFalse(s.isClosed()); assertFalse(foreign.isClosed());
        assertSame(foreign, KeycloakSessionUtil.getKeycloakSession());
    }
    @ParameterizedTest @ValueSource(booleans={false,true})
    void genericNativeHtmlErrorMappingIsAnExplicitUnsafeCounterexample(boolean realmPath) {
        NativeSession s = session(); HttpHeaders headers = mock(HttpHeaders.class);
        when(headers.getAcceptableMediaTypes()).thenReturn(List.of(MediaType.TEXT_HTML_TYPE));
        when(s.getContext().getRequestHeaders()).thenReturn(headers);
        KeycloakUriInfo uri = mock(KeycloakUriInfo.class); when(uri.getPath()).thenReturn(realmPath ? "/realms/"+HINT+"/protocol/openid-connect/token" : "/other-fixture-path");
        when(s.getContext().getUri()).thenReturn(uri);
        var denial = assertThrows(RealmEntryProbe.Denied.class, () -> RealmEntryProbe.beforeRealmResolution(s, HINT));
        Response fallback = KeycloakErrorHandler.getResponse(s, denial);
        assertEquals(500, fallback.getStatus()); assertEquals(1, s.realmAccess);
        verify(s.models).getRealmByName(realmPath ? HINT : org.keycloak.Config.getAdminRealm());
        // Native fallback attempted protected lookup after denial; never count this as a pass for safety.
    }
}
