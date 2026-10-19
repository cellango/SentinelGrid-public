/* SPDX-License-Identifier: Apache-2.0 */
package ai.sentinelgrid.research;

import java.util.Objects;
import java.util.concurrent.atomic.AtomicBoolean;
import org.keycloak.models.KeycloakSession;

/** Denial-only laboratory seam. Never durable enrollment or caller authority. */
public final class RealmEntryProbe {
    private RealmEntryProbe() {}
    public enum State { UNMANAGED_NATIVE_CONTROL, ENROLLED_CLOSED, UNKNOWN, AMBIGUOUS,
                        LOOKUP_ERROR, INCARNATION_MISMATCH }
    private static final ThreadLocal<Frame> ACTIVE = new ThreadLocal<>();
    private static final class Frame {
        final KeycloakSession session;
        final String hint;
        final State state;
        boolean rejected;
        Frame(KeycloakSession session, String hint, State state) {
            this.session = session; this.hint = hint; this.state = state;
        }
    }
    /** Explicit test-owner setup, never called by an HTTP handler or model/provider. */
    public static AutoCloseable fixture(KeycloakSession session, String hint, State state) {
        if (ACTIVE.get() != null) throw new IllegalStateException("Nested research fixture");
        Frame frame = new Frame(session, hint, Objects.requireNonNull(state));
        ACTIVE.set(frame);
        return () -> { if (ACTIVE.get() == frame) ACTIVE.remove(); };
    }
    public static void beforeRealmResolution(KeycloakSession session, String untrustedHint) {
        Frame frame = ACTIVE.get();
        if (session != null && frame != null && !frame.rejected && frame.state == State.UNMANAGED_NATIVE_CONTROL
                && frame.session == session && untrustedHint != null
                && Objects.equals(frame.hint, untrustedHint)) return;
        if (frame != null) frame.rejected = true;
        throw new Denied(session);
    }
    static void clearFixture() { ACTIVE.remove(); }
    public static final class Denied extends RuntimeException {
        final KeycloakSession session;
        final Thread owner = Thread.currentThread();
        final AtomicBoolean consumed = new AtomicBoolean();
        private volatile boolean cleanupFaultObserved;
        Denied(KeycloakSession session) { super("Research admission unavailable"); this.session = session; }
        public boolean cleanupFaultObserved() { return cleanupFaultObserved; }
        void failedCleanup() { cleanupFaultObserved = true; }
    }
}
