// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.research;

import java.util.Map;
import org.keycloak.models.RealmModel;

/** Denial-only research fixture. This is not durable or production enrollment. */
public final class EntryGuardProbe {
  public enum State { UNMANAGED_NATIVE_CONTROL, ENROLLED_CLOSED, UNKNOWN }
  private static final ThreadLocal<Map<String, State>> FIXTURE = new ThreadLocal<>();
  private EntryGuardProbe() {}

  /** Test JVM owner only; never called by application or protocol input. */
  public static AutoCloseable fixture(Map<String, State> states) {
    if (FIXTURE.get() != null) throw new IllegalStateException("Nested fixture scope");
    FIXTURE.set(Map.copyOf(states));
    return () -> FIXTURE.remove();
  }

  public static void beforeNativeDispatch(RealmModel realm) {
    Map<String, State> states=FIXTURE.get();
    String id=realm==null?null:realm.getId();
    if (states==null || id==null || states.get(id)!=State.UNMANAGED_NATIVE_CONTROL)
      throw new EntryDenied();
  }

  /** No HTTP/token exception conversion is claimed by this method-level fixture. */
  public static final class EntryDenied extends RuntimeException {
    public EntryDenied() { super("Research entry unavailable"); }
  }
}
