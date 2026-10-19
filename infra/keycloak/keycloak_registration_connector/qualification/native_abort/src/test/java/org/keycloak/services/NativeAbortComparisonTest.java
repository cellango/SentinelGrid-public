/* SPDX-License-Identifier: Apache-2.0 */
package org.keycloak.services;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.util.*;
import java.util.function.Consumer;
import org.junit.jupiter.api.*;
import org.keycloak.models.*;
import org.keycloak.provider.Provider;
import org.keycloak.tracing.*;
import org.keycloak.utils.KeycloakSessionUtil;
import org.keycloak.quarkus.runtime.transaction.TransactionalSessionHandler;
import io.opentelemetry.api.trace.Span;

class NativeAbortComparisonTest {
    static final String MODE=System.getProperty("abort.mode");
    static final boolean INTEGRATED="integrated".equals(MODE);
    static final class Tx extends AbstractKeycloakTransaction {
        int commits,rollbacks; RuntimeException rollbackFault,beginFault,statusFault; Runnable onRollback;
        protected void beginImpl() { if(beginFault!=null) throw beginFault; }
        protected void commitImpl() { commits++; }
        protected void rollbackImpl() { rollbacks++;if(onRollback!=null)onRollback.run();if(rollbackFault!=null)throw rollbackFault; }
        public boolean getRollbackOnly() { if(statusFault!=null) throw statusFault;return super.getRollbackOnly(); }
    }
    static class Session extends DefaultKeycloakSession {
        String trace="normal";boolean failClosed,failGetter;int closedQueries,getterCalls;
        final RuntimeException traceFault=new IllegalStateException("Synthetic trace");
        Runnable observer;
        Session() { this(mock(DefaultKeycloakSessionFactory.class)); }
        Session(DefaultKeycloakSessionFactory factory) { super(factory); }
        protected DefaultKeycloakContext createKeycloakContext(KeycloakSession s) { return mock(DefaultKeycloakContext.class); }
        public boolean isClosed() { closedQueries++;if(failClosed)throw new IllegalStateException("Synthetic isClosed");return super.isClosed(); }
        public KeycloakTransactionManager getTransactionManager() { getterCalls++;if(failGetter)throw new IllegalStateException("Synthetic getter");return super.getTransactionManager(); }
        public <T extends Provider>T getProvider(Class<T> type) {
            if(type!=TracingProvider.class)throw new AssertionError("Unreviewed provider");
            if(trace.equals("lookup"))throw traceFault;if(trace.equals("null"))return null;
            return type.cast(new NoopTracingProvider() {
                public void trace(Class<?> type,String phase,Consumer<Span> action) {
                    if(trace.equals("before"))throw traceFault;
                    if(trace.equals("drop"))return;
                    action.accept(getCurrentSpan());
                    if(trace.equals("repeat"))action.accept(getCurrentSpan());
                    if(observer!=null)observer.run();
                    if(trace.equals("after"))throw traceFault;
                }
            });
        }
    }
    static Throwable capture(Runnable action) { try {action.run();return null;}catch(Throwable t){return t;} }
    static ResearchAbortState attach(Session s,int capacity) {
        ResearchAbortState state=new ResearchAbortState(s,capacity);
        try { DefaultKeycloakSession.class.getMethod("attachResearchAbort",ResearchAbortState.class).invoke(s,state); }
        catch(ReflectiveOperationException e) { throw new AssertionError(e); }
        return state;
    }
    static KeycloakTransactionManager begin(Session s) {
        var tm=s.getTransactionManager();tm.setJTAPolicy(KeycloakTransactionManager.JTAPolicy.NOT_SUPPORTED);tm.begin();return tm;
    }
    @AfterEach void clear() { KeycloakSessionUtil.setKeycloakSession(null); }
    @Test void denyOnlyScopePreventsNativeUnmarkedDefaultCommit() {
        Session s=new Session();if(INTEGRATED)attach(s,8);Tx tx=new Tx();s.getTransactionManager().enlist(tx);begin(s);
        Throwable observed=capture(s::close);
        assertEquals(INTEGRATED?0:1,tx.commits);assertEquals(INTEGRATED?1:0,tx.rollbacks);
        assertEquals(INTEGRATED,observed instanceof ResearchAbortState.Denied);assertTrue(s.isClosed());
    }
    @Test void participantFaultObservationDoesNotFinishParticipant() {
        Session s=new Session();ResearchAbortState state=INTEGRATED?attach(s,8):null;
        Tx tx=new Tx();tx.rollbackFault=new IllegalStateException("Synthetic rollback");s.getTransactionManager().enlist(tx);var tm=begin(s);tm.setRollbackOnly();
        Throwable observed=capture(s::close);
        if(INTEGRATED) {assertInstanceOf(ResearchAbortState.Denied.class,observed);assertSame(tx.rollbackFault,state.failures().getFirst().error());}
        else if(MODE.equals("limited"))assertSame(tx.rollbackFault,observed);else assertNull(observed);
        assertEquals(AbstractKeycloakTransaction.TransactionState.STARTED,tx.getState());assertEquals(1,tx.rollbacks);assertEquals(0,tx.commits);
    }
    @Test void providerFailureRemainsUnreleasedResourceDespiteClosedSession() {
        Session s=new Session();ResearchAbortState state=INTEGRATED?attach(s,8):null;
        var tm=begin(s);tm.setRollbackOnly();RuntimeException fault=new IllegalStateException("Synthetic provider");int[] later={0};
        s.enlistForClose(()->{throw fault;});s.enlistForClose(()->later[0]++);
        Throwable observed=capture(s::close);
        if(INTEGRATED){assertInstanceOf(ResearchAbortState.Denied.class,observed);assertSame(fault,state.failures().getFirst().error());assertTrue(state.unknown());}else assertNull(observed);
        assertEquals(1,later[0]);assertTrue(s.isClosed());
    }
    @Test void silentObserverCannotOwnRequiredRollbackInIntegratedPath() {
        Session s=new Session();if(INTEGRATED)attach(s,8);Tx tx=new Tx();s.getTransactionManager().enlist(tx);var tm=begin(s);s.trace="drop";
        Throwable observed=capture(tm::rollback);assertEquals(INTEGRATED?1:0,tx.rollbacks);assertEquals(0,tx.commits);
        if(INTEGRATED)assertInstanceOf(ResearchAbortState.Denied.class,observed);else assertNull(observed);
        capture(s::close);
    }
    @Test void helperCannotUseFallibleClosedQueryAsAbortGate() {
        Session s=new Session();if(INTEGRATED)attach(s,8);Tx tx=new Tx();s.getTransactionManager().enlist(tx);var tm=begin(s);tm.setRollbackOnly();s.failClosed=true;
        Throwable observed=capture(()->new TransactionalSessionHandler(){}.close(s));assertNotNull(observed);
        assertEquals(INTEGRATED?1:0,tx.rollbacks);assertEquals(0,tx.commits);assertNull(KeycloakSessionUtil.getKeycloakSession());
        if(INTEGRATED)assertEquals(0,s.closedQueries);s.failClosed=false;capture(s::close);
    }
}
