/* SPDX-License-Identifier: Apache-2.0 */
package org.keycloak.services;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.util.*;
import java.util.function.Consumer;
import java.util.stream.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.*;
import org.keycloak.models.*;
import org.keycloak.provider.Provider;
import org.keycloak.tracing.*;
import org.keycloak.utils.KeycloakSessionUtil;
import org.keycloak.quarkus.runtime.transaction.TransactionalSessionHandler;
import io.opentelemetry.api.trace.Span;

/** Native code, synthetic participants. None of these states proves JDBC durability. */
class RollbackLifecycleTest {
    static final boolean CANDIDATE = Boolean.getBoolean("rollback.candidate");
    final List<Session> owned = new ArrayList<>();
    @AfterEach void dispose() {
        for (Session s : owned) if (!s.isClosed()) {
            s.getTransactionManager().setRollbackOnly();
            try { s.close(); } catch (RuntimeException ignored) { /* qualified fault */ }
        }
        KeycloakSessionUtil.setKeycloakSession(null);
    }
    static class Session extends DefaultKeycloakSession {
        String traceMode = "normal";
        final RuntimeException traceFailure = new IllegalStateException("Synthetic tracing failure");
        Session() { super(mock(DefaultKeycloakSessionFactory.class)); }
        protected DefaultKeycloakContext createKeycloakContext(KeycloakSession session) {
            return mock(DefaultKeycloakContext.class);
        }
        public <T extends Provider> T getProvider(Class<T> type) {
            if (type != TracingProvider.class) throw new AssertionError("Unexpected provider");
            if (traceMode.equals("lookup")) throw traceFailure;
            if (traceMode.equals("null")) return null;
            return type.cast(new NoopTracingProvider() {
                public void trace(Class<?> clazz, String name, Consumer<Span> action) {
                    if (traceMode.equals("before")) throw traceFailure;
                    if (traceMode.equals("drop")) return;
                    action.accept(getCurrentSpan());
                    if (traceMode.equals("after")) throw traceFailure;
                }
            });
        }
    }
    static class Tx extends AbstractKeycloakTransaction {
        final String id; final List<String> order;
        RuntimeException rollbackFailure; RuntimeException commitFailure;
        int commits; int rollbacks;
        Tx(String id, List<String> order) { this.id=id; this.order=order; }
        protected void commitImpl() { commits++; order.add("commit:"+id); if (commitFailure != null) throw commitFailure; }
        protected void rollbackImpl() { rollbacks++; order.add("rollback:"+id); if (rollbackFailure != null) throw rollbackFailure; }
    }
    Session session() { Session s=new Session(); owned.add(s); return s; }
    void begin(Session s) {
        s.getTransactionManager().setJTAPolicy(KeycloakTransactionManager.JTAPolicy.NOT_SUPPORTED);
        s.getTransactionManager().begin();
    }
    static RuntimeException capture(Runnable action) {
        try { action.run(); return null; } catch (RuntimeException failure) { return failure; }
    }
    static Stream<Arguments> failureGroups() {
        return Stream.of("ordinary","after").flatMap(group -> Stream.of("none","first","last","all","same")
            .map(which -> Arguments.of(group, which)));
    }
    @Test void compiledManagerSourceRatherThanDependencyJarIsLoaded() {
        assertTrue(DefaultKeycloakTransactionManager.class.getProtectionDomain().getCodeSource()
            .getLocation().getPath().endsWith("/target/classes/"));
    }
    @ParameterizedTest @MethodSource("failureGroups")
    void firstErrorAndLaterSuppressionPreserveAttempts(String group, String which) {
        Session s=session(); var tm=s.getTransactionManager(); List<String> order=new ArrayList<>();
        RuntimeException shared=new IllegalStateException("Synthetic shared failure");
        List<Tx> txs=new ArrayList<>(); List<RuntimeException> failures=new ArrayList<>();
        for (int i=0;i<3;i++) {
            Tx tx=new Tx("t"+i, order); txs.add(tx);
            if (which.equals("all") || which.equals("same") || (which.equals("first") && i==0) || (which.equals("last") && i==2)) {
                tx.rollbackFailure=which.equals("same") ? shared : new IllegalStateException("Synthetic failure "+i);
                failures.add(tx.rollbackFailure);
            }
            if (group.equals("ordinary")) tm.enlist(tx); else tm.enlistAfterCompletion(tx);
        }
        begin(s); RuntimeException observed=capture(tm::rollback);
        assertEquals(List.of("rollback:t0","rollback:t1","rollback:t2"), order);
        if (CANDIDATE && !failures.isEmpty()) {
            assertSame(failures.getFirst(),observed);
            assertArrayEquals(which.equals("same") ? new Throwable[0] : failures.stream().skip(1).toArray(Throwable[]::new), observed.getSuppressed());
        } else assertNull(observed);
        for (Tx tx : txs) {
            assertEquals(1,tx.rollbacks); assertEquals(0,tx.commits);
            assertEquals(tx.rollbackFailure==null ? AbstractKeycloakTransaction.TransactionState.FINISHED : AbstractKeycloakTransaction.TransactionState.STARTED,tx.getState());
        }
        assertFalse(tm.isActive()); tm.rollback();
        assertEquals(3,order.size(),"Completed-manager retry does not retry unfinished participants");
    }
    @Test void aggregationCrossesOrdinaryAndAfterCompletionLoops() {
        Session s=session(); var tm=s.getTransactionManager(); List<String> order=new ArrayList<>();
        Tx first=new Tx("main",order); Tx later=new Tx("after",order); Tx last=new Tx("healthy",order);
        first.rollbackFailure=new IllegalStateException("Synthetic first"); later.rollbackFailure=new IllegalStateException("Synthetic later");
        tm.enlist(first); tm.enlistAfterCompletion(later); tm.enlistAfterCompletion(last); begin(s);
        RuntimeException observed=capture(tm::rollback);
        if (CANDIDATE) { assertSame(first.rollbackFailure,observed); assertArrayEquals(new Throwable[]{later.rollbackFailure},observed.getSuppressed()); }
        else assertNull(observed);
        assertEquals(List.of("rollback:main","rollback:after","rollback:healthy"),order);
    }
    @Test void originalPrepareCauseIsPreservedByCandidateRollbackAggregation() {
        Session s=session(); var tm=s.getTransactionManager(); List<String> order=new ArrayList<>();
        Tx prep=new Tx("prepare",order), main=new Tx("main",order), after=new Tx("after",order);
        prep.commitFailure=new IllegalStateException("Synthetic prepare failure");
        main.rollbackFailure=new IllegalStateException("Synthetic ordinary rollback failure");
        after.rollbackFailure=new IllegalStateException("Synthetic after rollback failure");
        tm.enlistPrepare(prep); tm.enlist(main); tm.enlistAfterCompletion(after); begin(s);
        RuntimeException observed=capture(tm::commit);
        assertSame(CANDIDATE ? prep.commitFailure : after.rollbackFailure,observed);
        if (CANDIDATE) assertArrayEquals(new Throwable[]{main.rollbackFailure,after.rollbackFailure},observed.getSuppressed());
        else assertEquals(0,observed.getSuppressed().length);
        assertEquals(List.of("commit:prepare","rollback:main","rollback:after"),order);
        assertEquals(0,main.commits); assertEquals(0,after.commits);
    }
    @Test void prepareParticipantIsNotRolledBackByEitherVariant() {
        Session s=session(); var tm=s.getTransactionManager(); List<String> order=new ArrayList<>();
        Tx prep=new Tx("prepare",order), main=new Tx("main",order); tm.enlistPrepare(prep); tm.enlist(main); begin(s);
        assertNull(capture(tm::rollback)); assertEquals(0,prep.rollbacks);
        assertEquals(AbstractKeycloakTransaction.TransactionState.STARTED,prep.getState()); assertEquals(1,main.rollbacks);
        // Candidate does not add a prepare rollback contract or qualify those real callers.
    }
    @Test void mainCommitFailureStillDropsAfterCompletionRollbackErrors() {
        Session s=session(); var tm=s.getTransactionManager(); List<String> order=new ArrayList<>();
        Tx main=new Tx("main",order), after=new Tx("after",order), last=new Tx("healthy-after",order);
        main.commitFailure=new IllegalStateException("Synthetic main commit failure");
        after.rollbackFailure=new IllegalStateException("Synthetic after rollback failure");
        tm.enlist(main); tm.enlistAfterCompletion(after); tm.enlistAfterCompletion(last); begin(s);
        RuntimeException observed=capture(tm::commit); assertSame(main.commitFailure,observed);
        assertEquals(0,observed.getSuppressed().length); assertEquals(1,after.rollbacks); assertEquals(1,last.rollbacks);
        assertEquals(AbstractKeycloakTransaction.TransactionState.STARTED,after.getState());
    }
    @ParameterizedTest @ValueSource(strings={"lookup","null","before","after","drop"})
    void tracingFaultsKeepIncompleteCleanupExplicit(String mode) {
        Session s=session(); var tm=s.getTransactionManager(); List<String> order=new ArrayList<>();
        Tx first=new Tx("first",order), last=new Tx("last",order); tm.enlist(first); tm.enlist(last); begin(s); s.traceMode=mode;
        RuntimeException observed=capture(tm::rollback);
        if (mode.equals("lookup")) { assertSame(s.traceFailure,observed); assertTrue(tm.isActive()); }
        else {
            assertFalse(tm.isActive());
            if (CANDIDATE && !mode.equals("drop")) assertNotNull(observed); else assertNull(observed);
        }
        assertEquals(mode.equals("after") ? 1 : 0,first.rollbacks);
        assertEquals(mode.equals("after") ? 1 : 0,last.rollbacks);
        assertEquals(0,first.commits); assertEquals(0,last.commits);
        if (mode.equals("drop")) assertEquals(AbstractKeycloakTransaction.TransactionState.STARTED,first.getState());
    }
    @ParameterizedTest @ValueSource(booleans={false,true})
    void nativeSessionCloseAndThreadCleanupExposeOnlyTheCandidateParticipantFault(boolean participantFails) {
        Session s=session(); var tm=s.getTransactionManager(); List<String> order=new ArrayList<>(); Tx tx=new Tx("main",order);
        if (participantFails) tx.rollbackFailure=new IllegalStateException("Synthetic participant");
        tm.enlist(tx); begin(s); tm.setRollbackOnly(); KeycloakSessionUtil.setKeycloakSession(s);
        RuntimeException observed=capture(() -> new TransactionalSessionHandler() {}.close(s));
        if (CANDIDATE && participantFails) assertSame(tx.rollbackFailure,observed); else assertNull(observed);
        assertTrue(s.isClosed()); assertNull(KeycloakSessionUtil.getKeycloakSession()); assertEquals(0,tx.commits); assertEquals(1,tx.rollbacks);
        assertEquals(participantFails ? AbstractKeycloakTransaction.TransactionState.STARTED : AbstractKeycloakTransaction.TransactionState.FINISHED,tx.getState());
    }
    @ParameterizedTest @ValueSource(booleans={false,true})
    void providerCloseFaultIsLoggedWithoutPropagationEvenWhenSessionReportsClosed(boolean participantFails) {
        Session s=session(); List<String> order=new ArrayList<>(); Tx tx=new Tx("main",order);
        if (participantFails) tx.rollbackFailure=new IllegalStateException("Synthetic transaction failure");
        s.getTransactionManager().enlist(tx); begin(s); s.getTransactionManager().setRollbackOnly();
        int[] closes={0,0}; s.enlistForClose(() -> { closes[0]++; throw new IllegalStateException("Synthetic provider close failure"); });
        s.enlistForClose(() -> closes[1]++);
        RuntimeException observed=capture(s::close);
        if (CANDIDATE && participantFails) { assertSame(tx.rollbackFailure,observed); assertEquals(0,observed.getSuppressed().length); }
        else assertNull(observed);
        assertArrayEquals(new int[]{1,1},closes); assertTrue(s.isClosed());
        // Session close is not proof that every provider released its resources.
    }
    static class Unsuppressible extends RuntimeException { Unsuppressible() { super("Synthetic no-suppression primary",null,false,true); } }
    @Test void disabledSuppressionCannotRetainLaterFailureDetails() {
        Session s=session(); List<String> order=new ArrayList<>(); Tx first=new Tx("first",order),last=new Tx("last",order);
        first.rollbackFailure=new Unsuppressible(); last.rollbackFailure=new IllegalStateException("Synthetic later");
        s.getTransactionManager().enlist(first); s.getTransactionManager().enlist(last); begin(s);
        RuntimeException observed=capture(s.getTransactionManager()::rollback);
        if (CANDIDATE) { assertSame(first.rollbackFailure,observed); assertEquals(0,observed.getSuppressed().length); }
        else assertNull(observed);
        assertEquals(2,order.size());
    }
}
