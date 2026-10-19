/* SPDX-License-Identifier: Apache-2.0 */
package org.keycloak.services;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.keycloak.services.NativeAbortComparisonTest.capture;
import java.lang.reflect.Modifier;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Consumer;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.keycloak.models.*;
import org.keycloak.models.utils.*;
import org.keycloak.provider.*;
import org.keycloak.logging.*;
import org.keycloak.services.scheduled.*;
import org.keycloak.timer.ScheduledTask;
import org.keycloak.tracing.*;
import org.keycloak.transaction.*;
import org.keycloak.utils.KeycloakSessionUtil;
import org.keycloak.http.*;
import org.keycloak.quarkus.runtime.transaction.TransactionalSessionHandler;
import jakarta.ws.rs.container.AsyncResponse;
import jakarta.ws.rs.core.Response;
import io.opentelemetry.api.trace.Span;

/** Real native utility/context/core; controlled factory, models, tracing and response. No SQL/HTTP. */
class NativeSessionOwnershipTest {
    static final String RID="00000000-0000-4000-8000-000000000021";
    static final String CID="00000000-0000-4000-8000-000000000022";
    @BeforeAll static void profile(){org.keycloak.common.Profile.defaults();}
    @AfterAll static void reset(){org.keycloak.common.Profile.reset();}
    @AfterEach void clear(){KeycloakSessionUtil.setKeycloakSession(null);}
    static class Tx extends AbstractKeycloakTransaction {
        int begins,commits,rollbacks;RuntimeException beginFault,commitFault,rollbackFault;final List<String> events;
        Tx(List<String> events){this.events=events;}
        protected void beginImpl(){begins++;events.add("begin");if(beginFault!=null)throw beginFault;}
        protected void commitImpl(){commits++;events.add("commit");if(commitFault!=null)throw commitFault;}
        protected void rollbackImpl(){rollbacks++;events.add("rollback");if(rollbackFault!=null)throw rollbackFault;}
    }
    static class Factory extends DefaultKeycloakSessionFactory {
        final List<String> events=new ArrayList<>();final List<JobSession> created=new ArrayList<>();
        final Deque<Consumer<JobSession>> setups=new ArrayDeque<>();
        RuntimeException createFault;String traceMode="normal";int createCalls;
        final RuntimeException tracingFault=new IllegalStateException("Synthetic scheduled tracing");
        public KeycloakSession create(){
            createCalls++;events.add("create");if(createFault!=null)throw createFault;
            JobSession s=new JobSession(this);created.add(s);s.getTransactionManager().setJTAPolicy(KeycloakTransactionManager.JTAPolicy.NOT_SUPPORTED);
            s.getTransactionManager().enlist(s.tx);if(!setups.isEmpty())setups.removeFirst().accept(s);return s;
        }
        @SuppressWarnings("unchecked") public <T extends Provider> ProviderFactory<T> getProviderFactory(Class<T> type){
            if(type!=TracingProvider.class)throw new AssertionError("Unexpected provider factory");
            if(traceMode.equals("lookup"))throw tracingFault;
            return (ProviderFactory<T>)new NoopTracingProviderFactory(){
                public TracingProvider create(KeycloakSession ignored){return new NoopTracingProvider(){
                    public void trace(String n,String p,Consumer<Span> work){if(!traceMode.equals("drop"))work.accept(getCurrentSpan());}
                    public void close(){if(traceMode.equals("close"))throw tracingFault;}
                };}
            };
        }
    }
    static class JobSession extends DefaultKeycloakSession {
        final Factory f;final Tx tx;final RealmProvider realms=mock(RealmProvider.class);final ClientProvider clients=mock(ClientProvider.class);
        RuntimeException realmFault;boolean attributeFault;
        JobSession(Factory f){
            super(f);this.f=f;tx=new Tx(f.events);
            when(realms.getRealm(anyString())).thenAnswer(i->{f.events.add("realm.read");if(realmFault!=null)throw realmFault;return realm();});
            when(clients.getClientById(any(),anyString())).thenAnswer(i->{f.events.add("client.read");return client();});
        }
        protected DefaultKeycloakContext createKeycloakContext(KeycloakSession s){return new DefaultKeycloakContext(s){
            protected Optional<HttpRequest> createHttpRequest(){return Optional.empty();}
            protected Optional<HttpResponse> createHttpResponse(){return Optional.empty();}
        };}
        public RealmProvider realms(){return realms;}
        public ClientProvider clients(){return clients;}
        public Object getAttribute(String n){if(attributeFault)throw new IllegalStateException("Synthetic request-context attribute");return super.getAttribute(n);}
        public <T extends Provider>T getProvider(Class<T> type){
            if(type==TracingProvider.class)return type.cast(new NoopTracingProvider());
            if(type==MappedDiagnosticContextProvider.class)return type.cast(new NoopMappedDiagnosticContextProvider());
            throw new AssertionError("Unexpected provider");
        }
    }
    static RealmModel realm(){RealmModel r=mock(RealmModel.class);when(r.getId()).thenReturn(RID);return r;}
    static ClientModel client(){RealmModel r=realm();ClientModel c=mock(ClientModel.class);when(c.getId()).thenReturn(CID);when(c.getRealm()).thenReturn(r);return c;}
    static KeycloakContext context(){RealmModel r=realm();ClientModel cl=client();KeycloakContext c=mock(KeycloakContext.class);when(c.getRealm()).thenReturn(r);when(c.getClient()).thenReturn(cl);return c;}
    static Object job(Factory f,KeycloakContext c,KeycloakSessionTaskWithResult<Object> task){return KeycloakModelUtils.runJobInTransactionWithResult(f,c,task,"Synthetic ownership qualification");}
    static JobSession parent(){return new JobSession(new Factory());}
    @Test void exactNativeSourcesAreCompiled(){
        for(Class<?> c:List.of(KeycloakModelUtils.class,SessionLookup.class,RequestContextHelper.class,ScheduledTaskRunner.class,NamedSessionTask.class,DefaultKeycloakSessionFactory.class,DefaultKeycloakContext.class))
            assertTrue(c.getProtectionDomain().getCodeSource().getLocation().getPath().endsWith("/target/classes/"),c.getName());
        assertTrue(Modifier.isAbstract(DefaultKeycloakSessionFactory.class.getModifiers()));
        assertThrows(NoSuchMethodException.class,()->DefaultKeycloakSessionFactory.class.getDeclaredMethod("create"));
    }
    @Test void realJobBeginsAndClonesModelsBeforeBodyAndRestoresParent(){
        Factory f=new Factory();JobSession p=parent();KeycloakSessionUtil.setKeycloakSession(p);
        Object out=job(f,context(),s->{f.events.add("body");assertSame(s,KeycloakSessionUtil.getKeycloakSession());assertEquals(RID,s.getContext().getRealm().getId());assertEquals(CID,s.getContext().getClient().getId());return "synthetic-result";});
        assertEquals("synthetic-result",out);assertEquals(List.of("create","begin","realm.read","client.read","body","commit"),f.events);assertSame(p,KeycloakSessionUtil.getKeycloakSession());assertTrue(f.created.getFirst().isClosed());capture(p::close);
    }
    @Test void cloneLookupFaultRollsBackAndDoesNotReachBody(){
        Factory f=new Factory();RuntimeException fault=new IllegalStateException("Synthetic lookup");f.setups.add(s->s.realmFault=fault);int[] body={0};JobSession p=parent();KeycloakSessionUtil.setKeycloakSession(p);
        assertSame(fault,capture(()->job(f,context(),s->{body[0]++;return null;})));assertEquals(0,body[0]);assertEquals(1,f.created.getFirst().tx.rollbacks);assertEquals(0,f.created.getFirst().tx.commits);assertSame(p,KeycloakSessionUtil.getKeycloakSession());capture(p::close);
    }
    @Test void realJobBodyErrorRestoresParent(){
        Factory f=new Factory();RuntimeException fault=new IllegalStateException("Synthetic body");JobSession p=parent();KeycloakSessionUtil.setKeycloakSession(p);
        assertSame(fault,capture(()->job(f,null,s->{throw fault;})));assertEquals(1,f.created.getFirst().tx.rollbacks);assertSame(p,KeycloakSessionUtil.getKeycloakSession());capture(p::close);
    }
    @Test void factoryFailureStillRestoresParent(){
        Factory f=new Factory();f.createFault=new IllegalStateException("Synthetic creation");JobSession p=parent();KeycloakSessionUtil.setKeycloakSession(p);
        assertSame(f.createFault,capture(()->job(f,null,s->null)));assertEquals(0,f.created.size());assertSame(p,KeycloakSessionUtil.getKeycloakSession());capture(p::close);
    }
    @Test void contextAttributeFailurePrecedesBeginButIsNotAdmission(){
        Factory f=new Factory();f.setups.add(s->s.attributeFault=true);assertNotNull(capture(()->job(f,null,s->null)));JobSession s=f.created.getFirst();assertEquals(0,s.tx.begins+s.tx.commits+s.tx.rollbacks);assertTrue(s.isClosed());
    }
    @Test void partialNativeBeginCanLeaveAlreadyStartedParticipantUnfinished(){
        Factory f=new Factory();Tx[] extra={null};f.setups.add(s->{extra[0]=new Tx(f.events);extra[0].beginFault=new IllegalStateException("Synthetic begin");s.getTransactionManager().enlist(extra[0]);});
        assertNotNull(capture(()->job(f,null,s->null)));Tx first=f.created.getFirst().tx;assertEquals(1,first.begins);assertEquals(0,first.commits+first.rollbacks);assertEquals(AbstractKeycloakTransaction.TransactionState.STARTED,first.getState());
    }
    @Test void nativeJobResultCanReturnDespiteLoggedProviderCloseFailure(){
        Factory f=new Factory();f.setups.add(s->s.enlistForClose(()->{throw new IllegalStateException("Synthetic release");}));
        assertEquals("returned",job(f,null,s->"returned"));assertEquals(1,f.created.getFirst().tx.commits);assertTrue(f.created.getFirst().isClosed());
    }
    @Test void realNestedJobsRestoreEachImmediateParent(){
        Factory f=new Factory();JobSession p=parent();KeycloakSessionUtil.setKeycloakSession(p);
        job(f,null,outer->{job(f,null,inner->{assertSame(inner,KeycloakSessionUtil.getKeycloakSession());return null;});assertSame(outer,KeycloakSessionUtil.getKeycloakSession());return null;});
        assertEquals(2,f.created.size());assertTrue(f.created.stream().allMatch(s->s.tx.commits==1));assertSame(p,KeycloakSessionUtil.getKeycloakSession());capture(p::close);
    }
    @Test void realRollbackHelperOpensChildTransactionAndCommitsIndependentEffect(){
        Factory f=new Factory();JobSession outer=(JobSession)f.create();outer.getTransactionManager().begin();int[] effects={0};
        KeycloakModelUtils.enlistAfterRollback(outer,lookup->{assertSame(lookup.session(),KeycloakSessionUtil.getKeycloakSession());effects[0]++;});outer.getTransactionManager().setRollbackOnly();outer.close();
        assertEquals(1,effects[0]);assertEquals(1,outer.tx.rollbacks);assertEquals(2,f.created.size());assertEquals(1,f.created.get(1).tx.commits);
    }
    @ParameterizedTest @ValueSource(booleans={false,true})
    void realAfterCompletionHelperRunsIndependentJobOnEitherOutcome(boolean rollback){
        Factory f=new Factory();JobSession outer=(JobSession)f.create();outer.getTransactionManager().begin();int[] effects={0};
        KeycloakModelUtils.enlistAfterCompletion(outer,lookup->effects[0]++);if(rollback)outer.getTransactionManager().setRollbackOnly();outer.close();
        assertEquals(1,effects[0]);assertEquals(1,f.created.get(1).tx.commits);
    }
    @Test void rollbackOnlyHelperDoesNotRunItsJobOnCommit(){
        Factory f=new Factory();JobSession outer=(JobSession)f.create();outer.getTransactionManager().begin();int[] effects={0};KeycloakModelUtils.enlistAfterRollback(outer,lookup->effects[0]++);outer.close();assertEquals(0,effects[0]);assertEquals(1,f.created.size());
    }
    @Test void realJobRestoresParentButDoubleCloseStillFailsAfterGenericClose(){
        Factory f=new Factory();JobSession p=parent();KeycloakSessionUtil.setKeycloakSession(p);
        Throwable out=capture(()->job(f,null,s->{new TransactionalSessionHandler(){}.close(s);assertNull(KeycloakSessionUtil.getKeycloakSession());return null;}));assertInstanceOf(IllegalStateException.class,out);assertTrue(out.getMessage().contains("already closed"));assertSame(p,KeycloakSessionUtil.getKeycloakSession());capture(p::close);
    }
    @Test void workerHasItsOwnContextAndNoInheritedOwnerCheck() throws Exception {
        Factory f=new Factory();JobSession p=parent();KeycloakSessionUtil.setKeycloakSession(p);ExecutorService worker=Executors.newSingleThreadExecutor();
        try{assertNull(worker.submit(()->{assertNull(KeycloakSessionUtil.getKeycloakSession());job(f,context(),s->null);return KeycloakSessionUtil.getKeycloakSession();}).get());}finally{worker.shutdownNow();}
        assertSame(p,KeycloakSessionUtil.getKeycloakSession());assertEquals(1,f.created.getFirst().tx.commits);capture(p::close);
    }
    @Test void scheduledTaskUsesRealJobLifecycle(){
        Factory f=new Factory();int[] body={0};new ScheduledTaskRunner(f,s->body[0]++).run();assertEquals(1,body[0]);assertEquals(1,f.created.getFirst().tx.commits);
    }
    @Test void scheduledBodyFailureIsLoggedWithoutAnOutcomeReturn(){
        Factory f=new Factory();assertNull(capture(()->new ScheduledTaskRunner(f,s->{throw new IllegalStateException("Synthetic task");}).run()));assertEquals(1,f.created.getFirst().tx.rollbacks);assertEquals(0,f.created.getFirst().tx.commits);
    }
    @Test void scheduledTraceCanDropRequiredTaskInAdversarialControl(){
        Factory f=new Factory();f.traceMode="drop";int[] body={0};assertNull(capture(()->new ScheduledTaskRunner(f,s->body[0]++).run()));assertEquals(0,body[0]);assertEquals(0,f.createCalls);
    }
    @Test void scheduledTraceLookupFailureOccursOutsideCatch(){
        Factory f=new Factory();f.traceMode="lookup";assertSame(f.tracingFault,capture(()->new ScheduledTaskRunner(f,s->{}).run()));assertEquals(0,f.createCalls);
    }
    @Test void nativeAsyncResumePrecedesLaterCompletionFailure(){
        Factory f=new Factory();AsyncResponse response=mock(AsyncResponse.class);RuntimeException later=new IllegalStateException("Synthetic later completion");
        Throwable out=capture(()->job(f,null,s->{AsyncResponseTransaction.finishAsyncResponseInTransaction(s,response,Response.noContent().build());Tx after=new Tx(f.events);after.commitFault=later;s.getTransactionManager().enlistAfterCompletion(after);return null;}));
        assertSame(later,out);verify(response,times(1)).resume(any(Response.class));assertEquals(1,f.created.getFirst().tx.commits);
    }
    @Test void falseResumeResultDoesNotEstablishDeliveryButJobStillReturns(){
        Factory f=new Factory();AsyncResponse response=mock(AsyncResponse.class);when(response.resume(any(Response.class))).thenReturn(false);
        assertEquals("returned",job(f,null,s->{AsyncResponseTransaction.finishAsyncResponseInTransaction(s,response,Response.noContent().build());return "returned";}));verify(response).resume(any(Response.class));assertEquals(1,f.created.getFirst().tx.commits);
    }
    @Test void nativeSessionLookupReadsRecreatedContextRatherThanParentAuthority(){
        Factory f=new Factory();job(f,context(),s->{SessionLookup lookup=new SessionLookup(s);assertEquals(RID,lookup.realm().getId());assertSame(s,lookup.session());assertNull(lookup.findUserSession(null));return null;});assertEquals(1,f.created.getFirst().tx.commits);
    }
}
