/* SPDX-License-Identifier: Apache-2.0 */
package org.keycloak.services;

import java.util.*;
import org.keycloak.models.KeycloakTransaction;
import org.keycloak.tracing.TracingProvider;
import org.keycloak.utils.KeycloakSessionUtil;

/** Opt-in, deny-only fixture state. Never admission, recovery or durable rollback evidence. */
public final class ResearchAbortState {
    public record Failure(String phase, Throwable error) {}
    public static final class Denied extends RuntimeException {
        public final ResearchAbortState outcome;
        Denied(ResearchAbortState s) { super("Synthetic protected operation denied",null,false,false); outcome=s; }
    }
    private final DefaultKeycloakSession session;
    private final Thread owner=Thread.currentThread();
    private final int capacity;
    private final List<Failure> failures=new ArrayList<>();
    private final IdentityHashMap<KeycloakTransaction,String> registered=new IdentityHashMap<>();
    private final List<KeycloakTransaction> registrationOrder=new ArrayList<>();
    private final Map<String,Set<Object>> attempts=new HashMap<>();
    private volatile boolean terminal;
    private boolean managerStarted, closeStarted, overflow, unknown;
    public ResearchAbortState(DefaultKeycloakSession s, int capacity) {
        if (s==null || capacity<1 || capacity>64) throw new IllegalArgumentException("Bounded owned state required");
        this.session=s;this.capacity=capacity;
    }
    public synchronized void check(DefaultKeycloakSession s) {
        if (s!=session || Thread.currentThread()!=owner) {
            failure("ownership",new IllegalStateException("Synthetic foreign owner")); throw denied();
        }
    }
    public synchronized void before(DefaultKeycloakSession s,String phase) {
        check(s);if(terminal) { failure(phase,new IllegalStateException("Synthetic terminal abort"));throw denied(); }
    }
    public synchronized void remember(KeycloakTransaction tx,String role) {
        before(session,"register");
        if(registered.containsKey(tx) || registered.size()>=128) {
            failure("register",new IllegalStateException("Synthetic duplicate or bounded registration"));throw denied();
        }
        registered.put(tx,role);registrationOrder.add(tx);
    }
    public synchronized List<KeycloakTransaction> registrations() { return List.copyOf(registrationOrder); }
    public synchronized String role(KeycloakTransaction tx) { return registered.get(tx); }
    public synchronized void abort(Throwable cause) {
        check(session);terminal=true;if(cause!=null) failure("operation",cause);
    }
    public synchronized boolean startManager() {
        check(session);terminal=true;if(managerStarted) return false;managerStarted=true;return true;
    }
    public synchronized boolean startClose() {
        check(session);terminal=true;if(closeStarted) return false;closeStarted=true;return true;
    }
    public synchronized void failure(String phase,Throwable error) {
        terminal=true;unknown=true;
        if(failures.size()<capacity) failures.add(new Failure(phase,error));else overflow=true;
    }
    public synchronized List<Failure> failures() { return List.copyOf(failures); }
    public synchronized boolean overflow() { return overflow; }
    public synchronized boolean unknown() { return unknown; }
    public boolean terminal() { return terminal; }
    public Denied denied() { return new Denied(this); }
    public boolean run(String phase,Object key,Runnable work) {
        synchronized(this) {
            check(session);
            Set<Object> seen=attempts.computeIfAbsent(phase,k -> Collections.newSetFromMap(new IdentityHashMap<>()));
            if(!seen.add(key)) return false;
        }
        try { work.run();return true; }
        catch(Throwable error) {
            failure(phase,error);
            if(error instanceof VirtualMachineError || error instanceof ThreadDeath || error instanceof LinkageError) throw (Error)error;
            return false;
        }
    }
    public void observe(String phase) {
        run("trace:"+phase,this,() -> {
            TracingProvider trace=session.getProvider(TracingProvider.class);
            if(trace==null) throw new IllegalStateException("Synthetic missing tracing provider");
            // Observer never owns required participant execution.
            trace.trace(ResearchAbortState.class,phase,span -> {});
        });
    }
    public void clearContext() { run("context.clear",this,() -> KeycloakSessionUtil.setKeycloakSession(null)); }
}
