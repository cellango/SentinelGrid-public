// SPDX-License-Identifier: Apache-2.0
import com.sun.source.tree.*;
import com.sun.source.util.JavacTask;
import com.sun.source.util.TreePathScanner;
import com.sun.source.util.Trees;
import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import javax.tools.*;

/** Syntax inventory only. No symbol resolution, execution or enforcement claim. */
public final class CoreSourceAudit {
  private static String quote(String value) {
    StringBuilder out = new StringBuilder("\"");
    for (char c : value.toCharArray()) {
      if (c == '"' || c == '\\') out.append('\\').append(c);
      else if (c < 32) out.append(String.format("\\u%04x", (int)c));
      else out.append(c);
    }
    return out.append('"').toString();
  }

  private static final class Inventory extends TreePathScanner<Void, Void> {
    final CompilationUnitTree unit;
    final Trees trees;
    final BufferedWriter output;
    final String path;
    final Deque<String> classes = new ArrayDeque<>();
    final Deque<String> methods = new ArrayDeque<>();

    Inventory(CompilationUnitTree unit, Trees trees, Path root, BufferedWriter output) {
      this.unit=unit; this.trees=trees; this.output=output;
      this.path=root.relativize(Path.of(unit.getSourceFile().toUri()).toAbsolutePath().normalize()).toString();
    }
    void emit(String kind, Tree node, String name, String detail) {
      long pos=trees.getSourcePositions().getStartPosition(unit,node);
      long line=pos<0 ? -1 : unit.getLineMap().getLineNumber(pos);
      try {
        output.write("{\"kind\":"+quote(kind)+",\"path\":"+quote(path)
            +",\"owner\":"+quote(String.join(".",classes))
            +",\"method\":"+quote(methods.isEmpty()?"<initializer>":methods.peekLast())
            +",\"line\":"+line+",\"name\":"+quote(name)+",\"detail\":"+quote(detail)+"}\n");
      } catch (java.io.IOException error) { throw new java.io.UncheckedIOException(error); }
    }
    @Override public Void visitClass(ClassTree node,Void unused) {
      String name=node.getSimpleName().toString();
      classes.addLast(name.isEmpty()?"<anonymous>":name);
      emit("class",node,name,node.getKind().name());
      super.visitClass(node,unused); classes.removeLast(); return null;
    }
    @Override public Void visitMethod(MethodTree node,Void unused) {
      methods.addLast(node.getName()+"/"+node.getParameters().size());
      emit("method",node,node.getName().toString(),Integer.toString(node.getParameters().size()));
      for (AnnotationTree annotation:node.getModifiers().getAnnotations()) {
        Tree type=annotation.getAnnotationType();
        String name=type instanceof IdentifierTree id?id.getName().toString()
            :type instanceof MemberSelectTree member?member.getIdentifier().toString():"<unknown>";
        emit("annotation",annotation,name,type.getKind().name());
      }
      super.visitMethod(node,unused); methods.removeLast(); return null;
    }
    @Override public Void visitMethodInvocation(MethodInvocationTree node,Void unused) {
      ExpressionTree selector=node.getMethodSelect();
      String name=selector instanceof MemberSelectTree member?member.getIdentifier().toString()
          :selector instanceof IdentifierTree id?id.getName().toString():"<unknown>";
      emit("call",node,name,selector.getKind().name()+"/"+node.getArguments().size());
      return super.visitMethodInvocation(node,unused);
    }
    private void write(Tree node,ExpressionTree target) {
      String name=target instanceof MemberSelectTree member?member.getIdentifier().toString()
          :target instanceof IdentifierTree id?id.getName().toString():"<array-or-other>";
      emit("assignment",node,name,node.getKind().name());
    }
    @Override public Void visitAssignment(AssignmentTree node,Void unused) {
      write(node,node.getVariable()); return super.visitAssignment(node,unused);
    }
    @Override public Void visitCompoundAssignment(CompoundAssignmentTree node,Void unused) {
      write(node,node.getVariable()); return super.visitCompoundAssignment(node,unused);
    }
    @Override public Void visitUnary(UnaryTree node,Void unused) {
      if (Set.of(Tree.Kind.PREFIX_INCREMENT,Tree.Kind.POSTFIX_INCREMENT,
          Tree.Kind.PREFIX_DECREMENT,Tree.Kind.POSTFIX_DECREMENT).contains(node.getKind()))
        write(node,node.getExpression());
      return super.visitUnary(node,unused);
    }
  }

  public static void main(String[] args) throws Exception {
    if(args.length!=3) throw new IllegalArgumentException("source-root file-list output required");
    Path root=Path.of(args[0]).toAbsolutePath().normalize();
    List<Path> files=Files.readAllLines(Path.of(args[1]),StandardCharsets.UTF_8).stream()
        .map(root::resolve).toList();
    JavaCompiler compiler=ToolProvider.getSystemJavaCompiler();
    if(compiler==null) throw new IllegalStateException("A full JDK is required");
    DiagnosticCollector<JavaFileObject> diagnostics=new DiagnosticCollector<>();
    try(StandardJavaFileManager manager=compiler.getStandardFileManager(diagnostics,Locale.ROOT,StandardCharsets.UTF_8);
        BufferedWriter output=Files.newBufferedWriter(Path.of(args[2]),StandardCharsets.UTF_8)) {
      // Bound retained AST memory; parse only, never analyze or generate vendor classes.
      for(int start=0;start<files.size();start+=128) {
        var units=manager.getJavaFileObjectsFromPaths(files.subList(start,Math.min(start+128,files.size())));
        JavacTask task=(JavacTask)compiler.getTask(null,manager,diagnostics,
            List.of("-proc:none","--release","21"),null,units);
        Trees trees=Trees.instance(task);
        for(CompilationUnitTree unit:task.parse()) {
          Inventory inventory=new Inventory(unit,trees,root,output);
          inventory.emit("unit",unit,"",""); inventory.scan(unit,null);
        }
        if(diagnostics.getDiagnostics().stream().anyMatch(d->d.getKind()==Diagnostic.Kind.ERROR))
          throw new IllegalStateException("Vendor source parse failed; no source text or values emitted");
      }
    }
  }
}
