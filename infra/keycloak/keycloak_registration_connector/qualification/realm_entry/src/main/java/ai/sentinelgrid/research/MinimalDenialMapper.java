/* SPDX-License-Identifier: Apache-2.0 */
package ai.sentinelgrid.research;

import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.ExceptionMapper;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakTransactionManager;
import org.keycloak.quarkus.runtime.transaction.TransactionalSessionHandler;
import org.keycloak.utils.KeycloakSessionUtil;

/** Directly invoked fixture mapper. NOT registered into a real HTTP runtime. */
public final class MinimalDenialMapper implements ExceptionMapper<RealmEntryProbe.Denied> {
    private static final TransactionalSessionHandler NATIVE_CLOSE = new TransactionalSessionHandler() {};
    @Override
    public Response toResponse(RealmEntryProbe.Denied denial) {
        // A marker cannot transfer ownership to another thread or clean a foreign session.
        if (denial.owner != Thread.currentThread()) { denial.failedCleanup(); return response(); }
        if (!denial.consumed.compareAndSet(false, true)) return response();
        KeycloakSession session = denial.session;
        KeycloakSession current = KeycloakSessionUtil.getKeycloakSession();
        try {
            if (current != null && current != session) { denial.failedCleanup(); return response(); }
            if (session != null && !session.isClosed()) {
                boolean safeToClose = false;
                try {
                    KeycloakTransactionManager tx = session.getTransactionManager();
                    if (tx == null) throw new IllegalStateException("Missing transaction lifecycle");
                    if (tx.isActive()) {
                        tx.setRollbackOnly();
                        if (!tx.getRollbackOnly()) throw new IllegalStateException("Rollback marker refused");
                    }
                    safeToClose = true;
                } catch (RuntimeException failure) { denial.failedCleanup(); }
                // Never default-close an active transaction when rollback-only could not be proved.
                // This leaves cleanup incomplete and is an explicit NO-GO fault result.
                if (safeToClose) {
                    try { NATIVE_CLOSE.close(session); }
                    catch (RuntimeException failure) { denial.failedCleanup(); }
                }
            }
        } catch (RuntimeException lifecycleFailure) {
            denial.failedCleanup();
        } finally {
            RealmEntryProbe.clearFixture();
            if (KeycloakSessionUtil.getKeycloakSession() == session)
                KeycloakSessionUtil.setKeycloakSession(null);
        }
        return response();
    }
    private static Response response() {
        return Response.status(503).type(MediaType.APPLICATION_JSON_TYPE)
            .header("Cache-Control", "no-store").header("Pragma", "no-cache")
            .entity("{\"error\":\"temporarily_unavailable\"}").build();
    }
}
