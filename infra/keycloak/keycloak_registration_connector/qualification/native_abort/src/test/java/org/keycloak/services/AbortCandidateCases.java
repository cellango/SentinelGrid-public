/* SPDX-License-Identifier: Apache-2.0 */
package org.keycloak.services;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.keycloak.services.NativeAbortComparisonTest.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.keycloak.models.*;
import org.keycloak.provider.InvalidationHandler.ObjectType;
import org.keycloak.quarkus.runtime.transaction.TransactionalSessionHandler;
import org.keycloak.transaction.AsyncResponseTransaction;
import org.keycloak.utils.KeycloakSessionUtil;
import jakarta.ws.rs.container.AsyncResponse;
import jakarta.ws.rs.core.Response;

/** Integrated candidate only; real native core, synthetic participant/provider boundaries. */
class AbortCandidateCases {
    @AfterEach void clear() {KeycloakSessionUtil.setKeycloakSession(null);}
    @Test void exactNativeCoreClassesAreCompiled() {
        for(Class<?> c:List.of(DefaultKeycloakSession.class,DefaultKeycloakTransactionManager.class,AbstractKeycloakTransaction.class,TransactionalSessionHandler.class,AsyncResponseTransaction.class))
            assertTrue(c.getProtectionDomain().getCodeSource().getLocation().getPath().endsWith("/target/classes/"),c.getName());
    }
    @ParameterizedTest @ValueSource(strings={"normal","lookup","null","before","after","drop","repeat"})
    void requiredRollbackIsIndependentOfObserver(String mode) {
        Session s=new Session();ResearchAbortState st=attach(s,8);Tx first=new Tx(),last=new Tx();
        s.getTransactionManager().enlist(first);s.getTransactionManager().enlistAfterCompletion(last);var tm=begin(s);s.trace=mode;
        assertInstanceOf(ResearchAbortState.Denied.class,capture(tm::rollback));capture(s::close);capture(s::close);capture(tm::rollback);
        assertEquals(1,first.rollbacks);assertEquals(1,last.rollbacks);assertEquals(0,first.commits+last.commits);
        assertTrue(st.terminal());if(Set.of("lookup","null","before","after").contains(mode))assertTrue(st.unknown());
    }
    @Test void primarySecondaryEvidenceSurvivesDisabledSuppressionAndOverflow() {
        Session s=new Session();ResearchAbortState st=attach(s,3);
        RuntimeException primary=new RuntimeException("Synthetic primary",null,false,true){};st.abort(primary);
        for(int i=0;i<6;i++)st.run("failure:"+i,new Object(),()->{throw new IllegalStateException("Synthetic secondary");});
        assertSame(primary,st.failures().getFirst().error());assertEquals(3,st.failures().size());assertEquals(0,primary.getSuppressed().length);assertTrue(st.overflow());assertTrue(st.unknown());capture(s::close);
    }
    @Test void sameThrowableRetainsDistinctPhaseRecords() {
        Session s=new Session();ResearchAbortState st=attach(s,8);RuntimeException fault=new IllegalStateException("Synthetic shared");
        st.abort(fault);st.run("phase2",new Object(),()->{throw fault;});
        assertSame(fault,st.failures().get(0).error());assertSame(fault,st.failures().get(1).error());assertEquals("phase2",st.failures().get(1).phase());capture(s::close);
    }
    @Test void originalCauseAndLaterRollbackProviderInvalidationFaultsAreRetained() {
        DefaultKeycloakSessionFactory factory=mock(DefaultKeycloakSessionFactory.class);Session s=new Session(factory);ResearchAbortState st=attach(s,8);
        Tx tx=new Tx();tx.rollbackFault=new IllegalStateException("Synthetic rollback");s.getTransactionManager().enlist(tx);begin(s);
        RuntimeException primary=new IllegalStateException("Synthetic original");st.abort(primary);int[] later={0};
        s.enlistForClose(()->{throw new IllegalStateException("Synthetic close");});s.enlistForClose(()->later[0]++);
        s.invalidate(ObjectType.PROVIDER_FACTORY,"synthetic");doThrow(new IllegalStateException("Synthetic invalidation")).when(factory).invalidate(any(),any(),any(Object[].class));
        capture(s::close);assertEquals(1,later[0]);assertSame(primary,st.failures().getFirst().error());
        assertTrue(st.failures().stream().anyMatch(x->x.phase().equals("rollback")));assertTrue(st.failures().stream().anyMatch(x->x.phase().equals("provider.close")));assertTrue(st.failures().stream().anyMatch(x->x.phase().equals("invalidate")));assertEquals(0,tx.commits);
    }
    @Test void statusAndSessionGetterFaultCannotFallThroughToCommit() {
        Session s=new Session();ResearchAbortState st=attach(s,8);Tx tx=new Tx();s.getTransactionManager().enlist(tx);var tm=begin(s);
        tx.statusFault=new IllegalStateException("Synthetic status");assertFalse(st.run("status",tm,tm::getRollbackOnly));
        s.failGetter=true;capture(s::close);s.failGetter=false;assertEquals(1,tx.rollbacks);assertEquals(0,tx.commits);assertTrue(st.unknown());
    }
    @Test void failedBeginRetainsUnfinishedParticipantRatherThanClaimingCleanup() {
        Session s=new Session();ResearchAbortState st=attach(s,8);Tx bad=new Tx(),other=new Tx();bad.beginFault=new IllegalStateException("Synthetic partial begin");
        s.getTransactionManager().enlist(other);s.getTransactionManager().enlist(bad);var tm=s.getTransactionManager();tm.setJTAPolicy(KeycloakTransactionManager.JTAPolicy.NOT_SUPPORTED);
        assertFalse(st.run("begin",tm,tm::begin));capture(s::close);assertEquals(1,other.rollbacks);assertEquals(0,bad.rollbacks);assertEquals(0,bad.commits+other.commits);assertTrue(st.unknown());
    }
    @Test void failedActiveEnlistIsTrackedBeforeNativeBeginThrows() {
        Session s=new Session();ResearchAbortState st=attach(s,8);var tm=begin(s);Tx bad=new Tx();bad.beginFault=new IllegalStateException("Synthetic enlist begin");
        assertFalse(st.run("enlist",bad,()->tm.enlist(bad)));capture(s::close);assertTrue(st.failures().stream().anyMatch(x->x.phase().equals("rollback")));assertEquals(0,bad.commits);assertTrue(st.unknown());
    }
    @ParameterizedTest @ValueSource(strings={"begin","enlist","commit","rollback"})
    void terminalAbortRejectsResumeAndDoesNotReplay(String operation) {
        Session s=new Session();ResearchAbortState st=attach(s,8);Tx tx=new Tx();s.getTransactionManager().enlist(tx);var tm=begin(s);capture(tm::rollback);
        Throwable got=capture(()->{switch(operation){case "begin"->tm.begin();case "enlist"->tm.enlist(new Tx());case "commit"->tm.commit();default->tm.rollback();}});
        assertInstanceOf(ResearchAbortState.Denied.class,got);capture(s::close);assertEquals(1,tx.rollbacks);assertEquals(0,tx.commits);
    }
    @Test void reentrantTracingDoesNotRepeatRequiredWork() {
        Session s=new Session();ResearchAbortState st=attach(s,8);Tx tx=new Tx();s.getTransactionManager().enlist(tx);var tm=begin(s);s.observer=tm::rollback;
        capture(s::close);assertEquals(1,tx.rollbacks);assertEquals(0,tx.commits);assertTrue(st.unknown());
    }
    @Test void completedManagerNeverRetriesPossiblyCommittedWork() {
        Session s=new Session();Tx tx=new Tx();s.getTransactionManager().enlist(tx);var tm=begin(s);tm.commit();ResearchAbortState st=attach(s,8);capture(s::close);
        assertEquals(1,tx.commits);assertEquals(0,tx.rollbacks);assertTrue(st.failures().stream().anyMatch(x->x.phase().equals("manager.completed")));assertTrue(st.unknown());
    }
    @Test void foreignThreadCannotExecuteOwnedCallback() throws Exception {
        Session s=new Session();ResearchAbortState st=attach(s,8);Tx tx=new Tx();s.getTransactionManager().enlist(tx);var tm=begin(s);
        ExecutorService worker=Executors.newSingleThreadExecutor();try {assertInstanceOf(ResearchAbortState.Denied.class,worker.submit(()->capture(tm::rollback)).get());}finally{worker.shutdownNow();}
        assertEquals(0,tx.rollbacks);capture(s::close);assertEquals(1,tx.rollbacks);assertEquals(0,tx.commits);assertTrue(st.unknown());
    }
    @Test void foreignSessionCannotAdoptAnExistingOutcome() {
        Session s=new Session(),other=new Session();ResearchAbortState st=attach(s,8);
        assertThrows(java.lang.reflect.InvocationTargetException.class,()->DefaultKeycloakSession.class.getMethod("attachResearchAbort",ResearchAbortState.class).invoke(other,st));
        assertTrue(st.terminal());capture(s::close);capture(other::close);
    }
    @Test void duplicateRegistrationDoesNotDuplicateRollbackOrRelease() {
        Session s=new Session();ResearchAbortState st=attach(s,8);Tx tx=new Tx();var tm=s.getTransactionManager();tm.enlist(tx);
        assertInstanceOf(ResearchAbortState.Denied.class,capture(()->tm.enlistAfterCompletion(tx)));capture(s::close);assertEquals(0,tx.commits);assertTrue(st.unknown());
        // Never-started participant rollback is unknown, not successful release.
    }
    @Test void duplicateProviderIdentityIsClosedOnce() {
        Session s=new Session();attach(s,8);int[] n={0};org.keycloak.provider.Provider p=()->n[0]++;s.enlistForClose(p);s.enlistForClose(p);capture(s::close);capture(s::close);assertEquals(1,n[0]);
    }
    @Test void prepareIsNotBlindlyRolledBack() {
        Session s=new Session();attach(s,8);Tx prep=new Tx(),main=new Tx();s.getTransactionManager().enlistPrepare(prep);s.getTransactionManager().enlist(main);begin(s);capture(s::close);
        assertEquals(0,prep.commits+prep.rollbacks);assertEquals(AbstractKeycloakTransaction.TransactionState.STARTED,prep.getState());assertEquals(1,main.rollbacks);
    }
    @Test void actualAfterCallbackCanStillResumeAnErrorResponseNegativeContainmentWitness() {
        Session s=new Session();attach(s,8);AsyncResponse response=mock(AsyncResponse.class);
        AsyncResponseTransaction.finishAsyncResponseInTransaction(s,response,Response.status(401).build());begin(s);capture(s::close);
        verify(response,times(1)).resume(any(Response.class));
        // Deny-only outer close does not own all native response callbacks. LC-07 remains failed/unproved.
    }
    @Test void freshNativeChildSessionCanCommitDuringParentRollbackNegativeContainmentWitness() {
        Session parent=new Session();attach(parent,8);Tx outer=new Tx(),childTx=new Tx();
        outer.onRollback=()->{Session child=new Session();child.getTransactionManager().enlist(childTx);begin(child);child.close();};
        parent.getTransactionManager().enlist(outer);begin(parent);capture(parent::close);
        assertEquals(0,outer.commits);assertEquals(1,outer.rollbacks);assertEquals(1,childTx.commits);
        // Real native child-session lifecycle, not the actual job helper/provider. LC-06 remains open.
    }
    @Test void nativeHelperClearsButDoesNotRestoreNestedParentContextNegativeWitness() {
        Session s=new Session(),parent=new Session();ResearchAbortState st=attach(s,8);KeycloakSessionUtil.setKeycloakSession(parent);
        capture(()->new TransactionalSessionHandler(){}.close(s));assertNull(KeycloakSessionUtil.getKeycloakSession());assertNotSame(parent,KeycloakSessionUtil.getKeycloakSession());assertFalse(st.unknown(),"Lost parent context is not detected by the candidate");capture(parent::close);
    }
    @Test void fatalFailureKeepsUnknownAndMakesNoCleanupPromise() {
        Session s=new Session();ResearchAbortState st=attach(s,8);
        LinkageError fatal=new LinkageError("Synthetic fatal boundary");assertSame(fatal,capture(()->st.run("fatal",new Object(),()->{throw fatal;})));assertTrue(st.unknown());assertSame(fatal,st.failures().getFirst().error());capture(s::close);
    }
    @Test void markerLookupFailureStillPreventsDefaultCommit() {
        Session s=new Session();ResearchAbortState st=attach(s,8);Tx tx=new Tx();s.getTransactionManager().enlist(tx);begin(s);s.failGetter=true;
        assertFalse(st.run("marker.lookup",s,()->s.getTransactionManager().setRollbackOnly()));
        capture(s::close);s.failGetter=false;assertEquals(1,tx.rollbacks);assertEquals(0,tx.commits);assertEquals("marker.lookup",st.failures().getFirst().phase());
    }
    @Test void boundCommitDeniesBeforeNativePrepareOrMainCommit() {
        Session s=new Session();attach(s,8);Tx prep=new Tx(),main=new Tx();s.getTransactionManager().enlistPrepare(prep);s.getTransactionManager().enlist(main);var tm=begin(s);
        assertInstanceOf(ResearchAbortState.Denied.class,capture(tm::commit));capture(s::close);assertEquals(0,prep.commits+main.commits);assertEquals(1,main.rollbacks);assertEquals(0,prep.rollbacks);
    }
    @Test void lateAttachmentCannotClaimOwnershipOfAlreadyActiveParticipantNegativeWitness() {
        Session s=new Session();Tx tx=new Tx();s.getTransactionManager().enlist(tx);begin(s);ResearchAbortState st=attach(s,8);capture(s::close);
        assertEquals(0,tx.commits+tx.rollbacks);assertEquals(AbstractKeycloakTransaction.TransactionState.STARTED,tx.getState());assertTrue(st.unknown());
        assertEquals("manager.late_attach",st.failures().getFirst().phase());
    }

}
