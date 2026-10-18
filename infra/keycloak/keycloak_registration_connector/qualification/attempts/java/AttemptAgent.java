// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.lab.attempts;

import static net.bytebuddy.matcher.ElementMatchers.*;

import java.lang.instrument.Instrumentation;
import java.util.HashSet;
import java.util.Set;
import java.util.jar.JarFile;
import net.bytebuddy.agent.builder.AgentBuilder;
import net.bytebuddy.asm.Advice;
import net.bytebuddy.asm.AsmVisitorWrapper;
import net.bytebuddy.description.type.TypeDescription;
import net.bytebuddy.dynamic.DynamicType;
import net.bytebuddy.jar.asm.*;
import net.bytebuddy.utility.JavaModule;

/** Opt-in pinned disposable-lab tracing; never packaged in the provider artifact. */
public final class AttemptAgent {
  public static void premain(String helper, Instrumentation instrumentation) throws Exception {
    instrumentation.appendToBootstrapClassLoaderSearch(new JarFile(helper));
    Class.forName("ai.sentinelgrid.keycloak.lab.attempts.AttemptLog", true, null)
        .getMethod("start")
        .invoke(null);
    AgentBuilder b =
        new AgentBuilder.Default()
            .disableClassFormatChanges()
            .ignore(
                nameStartsWith("net.bytebuddy.")
                    .or(nameStartsWith("java."))
                    .or(nameStartsWith("jdk.")))
            .with(
                new AgentBuilder.Listener.Adapter() {
                  public void onTransformation(
                      TypeDescription t,
                      ClassLoader l,
                      JavaModule m,
                      boolean loaded,
                      DynamicType d) {
                    AttemptLog.transformed(t.getName());
                  }

                  public void onError(
                      String n, ClassLoader l, JavaModule m, boolean loaded, Throwable e) {
                    AttemptLog.failure();
                  }
                });
    b.type(
            namedOneOf(
                    "org.h2.jdbc.JdbcConnection",
                    "org.h2.jdbc.JdbcStatement",
                    "org.h2.jdbc.JdbcPreparedStatement",
                    "org.h2.engine.SessionLocal",
                    "org.h2.engine.SessionRemote",
                    "org.h2.command.Parser",
                    "org.h2.command.Command",
                    "org.h2.command.CommandContainer",
                    "org.h2.command.CommandRemote",
                    "org.h2.value.Transfer",
                    "org.h2.server.TcpServerThread",
                    "org.keycloak.quarkus.runtime.integration.resteasy.TransactionalSessionHandler",
                    "org.keycloak.quarkus.runtime.integration.jaxrs.CloseSessionFilter",
                    "ai.sentinelgrid.keycloak.lab.LabTrigger",
                    "ai.sentinelgrid.keycloak.registration.AssociationResource",
                    "org.keycloak.services.resources.admin.ClientResource",
                    "org.keycloak.services.resources.admin.UserResource",
                    "org.keycloak.protocol.oidc.endpoints.TokenEndpoint",
                    "ai.sentinelgrid.keycloak.lab.LabDatabase",
                    "ai.sentinelgrid.keycloak.lab.attempts.AttemptCalibration")
                .or(nameStartsWith("org.h2.command.ddl."))
                .or(nameStartsWith("org.h2.command.dml.")))
        .transform(
            (builder, t, l, m, p) -> {
              String n = t.getName();
              if (n.endsWith("resteasy.TransactionalSessionHandler"))
                return builder.visit(Advice.to(HttpAfterAdvice.class).on(named("handle")));
              if (n.endsWith("CloseSessionFilter"))
                return builder.visit(Advice.to(HttpCloseAdvice.class).on(named("closeSession")));
              if (n.endsWith("LabTrigger"))
                return builder.visit(Advice.to(RowAdvice.class).on(named("fire")));
              if (n.equals("org.h2.value.Transfer"))
                return builder
                    .visit(Advice.to(WriteAdvice.class).on(named("writeInt")))
                    .visit(Advice.to(ReadAdvice.class).on(named("readInt")));
              if (n.equals("org.h2.server.TcpServerThread"))
                return builder.visit(Advice.to(ServerAdvice.class).on(named("process")));
              if (n.startsWith("org.h2.")) {
                builder =
                    builder.visit(
                        Advice.to(SpanAdvice.class)
                            .on(
                                isMethod()
                                    .and(not(isAbstract()))
                                    .and(
                                        namedOneOf(
                                                "prepareStatement",
                                                "prepareCall",
                                                "prepareCommand",
                                                "prepareLocal",
                                                "prepare",
                                                "recompileIfRequired",
                                                "execute",
                                                "executeQuery",
                                                "executeUpdate",
                                                "executeLargeUpdate",
                                                "executeUpdateInternal",
                                                "executeBatch",
                                                "executeLargeBatch",
                                                "addBatch",
                                                "setString",
                                                "setInt",
                                                "setObject",
                                                "setNull",
                                                "commit",
                                                "rollback",
                                                "rollbackToSavepoint",
                                                "setSavepoint",
                                                "setAutoCommit",
                                                "update",
                                                "query",
                                                "close",
                                                "stop")
                                            .or(
                                                nameStartsWith("set")
                                                    .and(
                                                        isDeclaredBy(
                                                            named(
                                                                "org.h2.jdbc.JdbcPreparedStatement")))))));
                if (n.equals("org.h2.engine.SessionRemote"))
                  builder = builder.visit(Advice.to(TraceAdvice.class).on(named("traceOperation")));
                return builder;
              }
              builder =
                  builder.visit(
                      Advice.to(SpanAdvice.class)
                          .on(isMethod().and(isPublic()).and(not(isAbstract()))));
              if (n.endsWith("AssociationResource")) {
                builder =
                    builder.visit(
                        new AsmVisitorWrapper.ForDeclaredMethods()
                            .writerFlags(ClassWriter.COMPUTE_FRAMES)
                            .method(
                                named("read"),
                                (type, method, visitor, context, pool, writer, reader) ->
                                    new MethodVisitor(Opcodes.ASM9, visitor) {
                                      final Set<Label> handlers = new HashSet<>();

                                      public void visitTryCatchBlock(
                                          Label start, Label end, Label handler, String type) {
                                        if ("java/lang/RuntimeException".equals(type))
                                          handlers.add(handler);
                                        super.visitTryCatchBlock(start, end, handler, type);
                                      }

                                      public void visitLabel(Label label) {
                                        super.visitLabel(label);
                                        if (handlers.contains(label)) {
                                          super.visitInsn(Opcodes.DUP);
                                          super.visitMethodInsn(
                                              Opcodes.INVOKESTATIC,
                                              "ai/sentinelgrid/keycloak/lab/attempts/AttemptLog",
                                              "caught",
                                              "(Ljava/lang/Throwable;)V",
                                              false);
                                        }
                                      }
                                    }));
              }
              return builder;
            })
        .installOn(instrumentation);
  }

  public static class HttpAfterAdvice {
    @Advice.OnMethodExit(suppress = Throwable.class)
    public static void exit(@Advice.This Object owner) {
      AttemptLog.httpAfterHandler(owner);
    }
  }

  public static class HttpCloseAdvice {
    @Advice.OnMethodEnter(suppress = Throwable.class)
    public static void enter(@Advice.This Object owner) {
      AttemptLog.httpBeforeClose(owner);
    }

    @Advice.OnMethodExit(onThrowable = Throwable.class, suppress = Throwable.class)
    public static void exit(@Advice.This Object owner) {
      AttemptLog.httpAfterClose(owner);
    }
  }

  public static class RowAdvice {
    @Advice.OnMethodEnter(suppress = Throwable.class)
    public static void enter(
        @Advice.This Object owner,
        @Advice.Argument(1) Object oldRow,
        @Advice.Argument(2) Object newRow) {
      AttemptLog.row(owner, oldRow, newRow);
    }
  }

  public static class SpanAdvice {
    @Advice.OnMethodEnter(suppress = Throwable.class)
    public static long enter(
        @Advice.This(optional = true) Object owner,
        @Advice.Origin("#t.#m") String hook,
        @Advice.AllArguments Object[] args) {
      return AttemptLog.enter(owner, hook, args);
    }

    @Advice.OnMethodExit(onThrowable = Throwable.class, suppress = Throwable.class)
    public static void exit(@Advice.Enter long id, @Advice.Thrown Throwable e) {
      AttemptLog.exit(id, e);
    }
  }

  public static class TraceAdvice {
    @Advice.OnMethodEnter(suppress = Throwable.class)
    public static void enter(@Advice.Argument(0) String operation) {
      AttemptLog.trace(operation);
    }
  }

  public static class WriteAdvice {
    @Advice.OnMethodEnter(suppress = Throwable.class)
    public static void enter(@Advice.This Object owner, @Advice.Argument(0) int n) {
      AttemptLog.writeInt(owner, n);
    }
  }

  public static class ReadAdvice {
    @Advice.OnMethodExit(suppress = Throwable.class)
    public static void exit(@Advice.Return int n) {
      AttemptLog.readInt(n);
    }
  }

  public static class ServerAdvice {
    @Advice.OnMethodEnter(suppress = Throwable.class)
    public static void enter(@Advice.This Object owner) {
      AttemptLog.serverEnter(owner);
    }

    @Advice.OnMethodExit(onThrowable = Throwable.class, suppress = Throwable.class)
    public static void exit(@Advice.Thrown Throwable e) {
      AttemptLog.serverExit(e);
    }
  }
}
