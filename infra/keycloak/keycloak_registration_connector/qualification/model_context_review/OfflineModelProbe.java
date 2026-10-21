import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.function.Consumer;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.*;
import org.apache.maven.model.*;
import org.apache.maven.model.building.*;
import org.apache.maven.model.profile.*;
import org.apache.maven.model.resolution.*;

/** Exact owned model-only experiment. No Maven CLI, extensions or artifact fetch. */
public final class OfflineModelProbe {
    record ModelCase(String id, String coordinate, int validationLevel, String expectation) {}
    static final List<ModelCase> CONTEXTS = List.of(
        new ModelCase("surefire_strict_with_reviewed_BOM", "org.apache.maven.plugins:maven-surefire-plugin:3.5.6", 31, "model_only_success"),
        new ModelCase("jctools_strict_retained_negative", "org.jctools:jctools-core:4.0.5", 31, "expected_strict_denial"),
        new ModelCase("jctools_project_default_comparison", "org.jctools:jctools-core:4.0.5", 30, "model_only_success"),
        new ModelCase("jctools_descriptor_validation_comparison", "org.jctools:jctools-core:4.0.5", 0, "model_only_success"));
    record Pin(String coordinate, String digest, Path path) {}
    static final Map<String, Pin> pins = new TreeMap<>();
    static final List<String> requests = new ArrayList<>(), repositoryIds = new ArrayList<>();
    static int passed;
    static String quote(String value) { return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "\""; }
    static void result(String name, String state, String detail) { System.out.println("{\"name\":" + quote(name) + ",\"outcome\":" + quote(state) + ",\"detail\":" + quote(detail) + "}"); }
    static void require(boolean condition, String message) { if (!condition) throw new IllegalStateException(message); }
    static String digest(byte[] data) throws Exception { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data)); }
    static Element element(Element parent, String name) {
        for (Node node = parent.getFirstChild(); node != null; node = node.getNextSibling()) if (node instanceof Element && name.equals(node.getLocalName() == null ? node.getNodeName() : node.getLocalName())) return (Element) node;
        return null;
    }
    static String value(Element parent, String name) { Element child = parent == null ? null : element(parent, name); return child == null ? null : child.getTextContent().trim(); }
    static byte[] checked(Pin pin) throws Exception {
        require(!Files.isSymbolicLink(pin.path()), "SYMLINK_INPUT");
        byte[] data = Files.readAllBytes(pin.path());
        require(digest(data).equals(pin.digest()), "HASH_DRIFT");
        String xml = new String(data, StandardCharsets.UTF_8);
        require(!xml.toLowerCase(Locale.ROOT).contains("<!doctype") && !xml.toLowerCase(Locale.ROOT).contains("<!entity"), "DTD_ENTITY_FORBIDDEN");
        DocumentBuilderFactory factory = DocumentBuilderFactory.newDefaultInstance();
        factory.setNamespaceAware(true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        factory.setExpandEntityReferences(false);
        Element project = factory.newDocumentBuilder().parse(new ByteArrayInputStream(data)).getDocumentElement();
        String ns = project.getNamespaceURI();
        require((ns == null || ns.equals("http://maven.apache.org/POM/4.0.0")) && ("project".equals(project.getLocalName()) || "project".equals(project.getNodeName())), "MODEL_NAMESPACE");
        String group = value(project, "groupId"), version = value(project, "version");
        Element parent = element(project, "parent");
        if (group == null) group = value(parent, "groupId");
        if (version == null) version = value(parent, "version");
        require(pin.coordinate().equals(group + ":" + value(project, "artifactId") + ":" + version), "FOREIGN_IDENTITY");
        return data;
    }
    static final class BytesSource implements ModelSource {
        final String coordinate; final byte[] bytes;
        BytesSource(String coordinate, byte[] bytes) { this.coordinate = coordinate; this.bytes = bytes; }
        public InputStream getInputStream() { return new ByteArrayInputStream(bytes); }
        public String getLocation() { return "pinned:" + coordinate; }
    }
    static final class PinnedResolver implements ModelResolver {
        public ModelSource resolveModel(String group, String artifact, String version) throws UnresolvableModelException {
            String c = group + ":" + artifact + ":" + version;
            requests.add(c);
            if (!group.matches("[A-Za-z0-9_.-]+") || !artifact.matches("[A-Za-z0-9_.-]+") || !version.matches("[A-Za-z0-9_.-]+") || !pins.containsKey(c)) throw new UnresolvableModelException("UNPINNED_COORDINATE", group, artifact, version);
            try { return new BytesSource(c, checked(pins.get(c))); }
            catch (Exception failure) { throw new UnresolvableModelException("INPUT_DENIED:" + failure.getMessage(), group, artifact, version, failure); }
        }
        public ModelSource resolveModel(Parent parent) throws UnresolvableModelException { return resolveModel(parent.getGroupId(), parent.getArtifactId(), parent.getVersion()); }
        public ModelSource resolveModel(Dependency dependency) throws UnresolvableModelException { return resolveModel(dependency.getGroupId(), dependency.getArtifactId(), dependency.getVersion()); }
        public void addRepository(Repository repository) { repositoryIds.add(repository.getId()); } // Data only: no URL, path, transport or loader API.
        public void addRepository(Repository repository, boolean replace) { addRepository(repository); }
        public ModelResolver newCopy() { return new PinnedResolver(); }
    }
    static ModelBuildingResult model(String coordinate, Set<String> selected) throws Exception {
        return modelAtLevel(coordinate, selected, ModelBuildingRequest.VALIDATION_LEVEL_MAVEN_3_1);
    }
    static ModelBuildingResult contextualModel(ModelCase context, Set<String> selected) throws Exception {
        require(CONTEXTS.contains(context), "UNREVIEWED_CONTEXT");
        if (context.validationLevel() != ModelBuildingRequest.VALIDATION_LEVEL_MAVEN_3_1)
            require(context.coordinate().equals("org.jctools:jctools-core:4.0.5"), "UNREVIEWED_VALIDATION_TARGET");
        return modelAtLevel(context.coordinate(), selected, context.validationLevel());
    }
    private static ModelBuildingResult modelAtLevel(String coordinate, Set<String> selected, int validationLevel) throws Exception {
        Set<String> allowed = coordinate.startsWith("review.fixture:") ? Set.of("review") : Set.of("crypto-default", "upstream-adapters");
        require(allowed.containsAll(selected), "UNREVIEWED_PROFILE");
        DefaultModelBuilderFactory factory = new DefaultModelBuilderFactory() {
            protected ProfileSelector newProfileSelector() {
                return (profiles, context, problems) -> {
                    List<Profile> active = new ArrayList<>();
                    for (Profile profile : profiles) if (selected.contains(profile.getId())) active.add(profile);
                    return active; // No file/JDK/OS/property/activeByDefault discovery.
                };
            }
            protected org.apache.maven.model.locator.ModelLocator newModelLocator() { return directory -> { throw new IllegalStateException("LOCAL_MODEL_LOOKUP_FORBIDDEN"); }; }
        };
        Pin pin = pins.get(coordinate); require(pin != null, "UNPINNED_TARGET");
        ModelBuildingRequest request = new DefaultModelBuildingRequest()
                .setModelSource(new BytesSource(coordinate, checked(pin)))
                .setModelResolver(new PinnedResolver()).setProcessPlugins(false)
                .setSystemProperties(new Properties()).setUserProperties(new Properties())
                .setProfiles(List.of()).setActiveProfileIds(new ArrayList<>(selected)).setInactiveProfileIds(List.of())
                .setBuildStartTime(new Date(0)).setLocationTracking(false).setTwoPhaseBuilding(false)
                .setValidationLevel(validationLevel);
        return factory.newInstance().build(request);
    }
    interface CheckedOperation { void run() throws Exception; }
    static void positive(String name, CheckedOperation operation) throws Exception { operation.run(); passed++; result(name, "passed", "bounded model/control only"); }
    static void negative(String name, CheckedOperation operation, String message) throws Exception {
        try { operation.run(); } catch (Exception expected) {
            String text = expected.toString();
            for (Throwable cause = expected.getCause(); cause != null; cause = cause.getCause()) text += " " + cause;
            require(text.contains(message), name + ": unexpected error " + text); passed++; result(name, "expected_denial", message); return;
        }
        throw new IllegalStateException(name + ": missing denial");
    }
    public static void main(String[] args) throws Exception {
        Path input = Path.of(args[0]), work = Path.of(args[1]), canary = Path.of(args[2]);
        for (String line : Files.readAllLines(input.resolve("pins.tsv"), StandardCharsets.UTF_8)) {
            String[] f = line.split("\t", -1); require(f.length == 3 && !pins.containsKey(f[0]), "DUPLICATE_PIN");
            Path path = input.resolve(f[2]).normalize(); require(path.startsWith(input) && !path.equals(input), "UNOWNED_PATH");
            Pin pin = new Pin(f[0], f[1], path); checked(pin); pins.put(f[0], pin);
        }
        // Guard is installed before JVM start; these effects precede creating the model builder.
        positive("owned_work_write", () -> Files.writeString(work.resolve("inside.txt"), "OWNED_MODEL_CONTROL"));
        negative("outside_canary_read", () -> Files.readString(canary), "Operation not permitted");
        negative("read_only_input_write", () -> Files.writeString(input.resolve("read-only-canary.txt"), "MUST_BE_DENIED"), "Operation not permitted");
        negative("socket_bind_no_listener", () -> { try (Socket socket = new Socket()) { socket.bind(new InetSocketAddress("127.0.0.1", 0)); } }, "Operation not permitted");
        positive("sanitized_stdin", () -> require(System.in.read() == -1, "INHERITED_INPUT"));
        positive("synthetic_parent_BOM_inheritance", () -> {
            Model m = model("review.fixture:child:1", Set.of()).getEffectiveModel();
            require(m.getDependencies().get(0).getVersion().equals("2"), "BOM_VERSION");
            require(m.getProperties().getProperty("profile.value").equals("base"), "AUTO_PROFILE_ACTIVATED");
            require(repositoryIds.contains("ignored-review-repository"), "REPOSITORY_CALLBACK_NOT_EXERCISED");
        });
        positive("explicit_synthetic_profile", () -> require(model("review.fixture:child:1", Set.of("review")).getEffectiveModel().getProperties().getProperty("profile.value").equals("reviewed"), "PROFILE_NOT_SELECTED"));
        negative("unknown_profile", () -> model("review.fixture:child:1", Set.of("unknown")), "UNREVIEWED_PROFILE");
        Pin saved = pins.remove("review.fixture:parent:1");
        negative("missing_parent_no_fetch", () -> model("review.fixture:child:1", Set.of()), "UNPINNED_COORDINATE"); pins.put(saved.coordinate(), saved);
        negative("unknown_version_range", () -> new PinnedResolver().resolveModel("review.fixture", "parent", "[1,2)"), "UNPINNED_COORDINATE");
        Pin bom = pins.get("review.fixture:bom:1");
        pins.put(saved.coordinate(), new Pin(saved.coordinate(), bom.digest(), bom.path()));
        negative("foreign_coordinate_payload", () -> model("review.fixture:child:1", Set.of()), "FOREIGN_IDENTITY"); pins.put(saved.coordinate(), saved);
        pins.put(saved.coordinate(), new Pin(saved.coordinate(), "0".repeat(64), saved.path()));
        negative("forged_digest", () -> model("review.fixture:child:1", Set.of()), "HASH_DRIFT"); pins.put(saved.coordinate(), saved);
        positive("DTD_entity_rejected_before_model", () -> {
            Path path = work.resolve("doctype.pom"); byte[] bytes = "<!DOCTYPE project [<!ENTITY x SYSTEM 'file:///must-never-be-opened'>]><project/>".getBytes(StandardCharsets.UTF_8);Files.write(path, bytes);
            negative("DTD_payload", () -> checked(new Pin("review.fixture:blocked:1", digest(bytes), path)), "DTD_ENTITY_FORBIDDEN");
        });
        negative("incomplete_native_profile_selection", () -> model("org.keycloak:keycloak-parent:26.8.1", Set.of("crypto-default")), "ee.maven.groupId");
        negative("foreign_target_context_denied", () -> contextualModel(new ModelCase("unreviewed", "org.keycloak:keycloak-parent:26.8.1", 0, "model_only_success"), Set.of("crypto-default", "upstream-adapters")), "UNREVIEWED_CONTEXT");
        Pin reviewedBom = pins.remove("org.junit:junit-bom:5.12.2");
        require(reviewedBom != null, "REVIEWED_BOM_MISSING");
        negative("surefire_missing_BOM_retained_negative", () -> model("org.apache.maven.plugins:maven-surefire-plugin:3.5.6", Set.of("crypto-default", "upstream-adapters")), "UNPINNED_COORDINATE");
        pins.put(reviewedBom.coordinate(), reviewedBom);
        long totalOutputBytes = 0;
        for (int index = 0; index < CONTEXTS.size(); index++) {
            ModelCase context = CONTEXTS.get(index);
            int firstRequest = requests.size(), firstRepository = repositoryIds.size();
            String outputId = String.format(Locale.ROOT, "context-%04d", index);
            String metadata = "output=" + outputId + ";validation=" + context.validationLevel();
            ModelBuildingResult built;
            try { built = contextualModel(context, Set.of("crypto-default", "upstream-adapters")); }
            catch (ModelBuildingException failure) {
                String outcome = "NO_GO";
                if (context.expectation().equals("expected_strict_denial")) {
                    require(failure.toString().contains("duplicate declaration of plugin org.apache.felix:maven-bundle-plugin"), "STRICT_FAILURE_CHANGED");
                    outcome = "expected_strict_denial";
                }
                result("selected_context_model:" + context.id(), outcome, metadata + ";request_start=" + firstRequest + ";request_end=" + requests.size() + ";repository_start=" + firstRepository + ";repository_end=" + repositoryIds.size() + ";failure=" + failure); continue;
            }
            require(!context.expectation().equals("expected_strict_denial"), "STRICT_NEGATIVE_LOST");
            Model effective = built.getEffectiveModel();
            require(context.coordinate().equals(effective.getGroupId() + ":" + effective.getArtifactId() + ":" + effective.getVersion()), "EFFECTIVE_IDENTITY");
            List<String> dependencies = new ArrayList<>();
            for (Dependency dep : effective.getDependencies()) dependencies.add(dep.getGroupId() + ":" + dep.getArtifactId() + ":" + dep.getVersion() + ":" + dep.getType() + ":" + dep.getClassifier() + ":" + dep.getScope() + ":optional=" + dep.isOptional() + ":exclusions=" + dep.getExclusions().size());
            List<String> problems = new ArrayList<>();
            boolean duplicateWarning = false;
            for (ModelProblem problem : built.getProblems()) {
                problems.add(problem.getSeverity() + ":" + problem.getMessage());
                if (problem.getSeverity() == ModelProblem.Severity.WARNING && problem.getMessage().contains("duplicate declaration of plugin org.apache.felix:maven-bundle-plugin")) duplicateWarning = true;
            }
            if (context.validationLevel() == ModelBuildingRequest.VALIDATION_LEVEL_MAVEN_3_0) require(duplicateWarning, "PROJECT_WARNING_LOST");
            StringWriter xml = new StringWriter();
            new org.apache.maven.model.io.xpp3.MavenXpp3Writer().write(xml, effective);
            List<String> provenance = new ArrayList<>();
            provenance.add("case=" + context.id() + "\tvalidation=" + context.validationLevel());
            for (String id : built.getModelIds()) {
                List<String> active = new ArrayList<>();
                for (Profile profile : built.getActivePomProfiles(id)) active.add(profile.getId());
                provenance.add("model=" + id + "\tactive_explicit_profiles=" + String.join(",", active));
            }
            for (String request : requests.subList(firstRequest, requests.size())) provenance.add("resolver=" + request);
            for (String repository : repositoryIds.subList(firstRepository, repositoryIds.size())) provenance.add("ignored_repository_id=" + repository);
            Map<String, String> outputs = new LinkedHashMap<>();
            outputs.put(".effective.xml", xml.toString());
            outputs.put(".dependencies.txt", String.join("\n", dependencies) + "\n");
            outputs.put(".provenance.txt", String.join("\n", provenance) + "\n");
            outputs.put(".problems.txt", String.join("\n", problems) + "\n");
            for (Map.Entry<String, String> output : outputs.entrySet()) {
                byte[] bytes = output.getValue().getBytes(StandardCharsets.UTF_8);
                require(bytes.length <= 8 * 1024 * 1024, "TARGET_OUTPUT_BOUND");
                totalOutputBytes += bytes.length;require(totalOutputBytes <= 256L * 1024 * 1024, "TOTAL_OUTPUT_BOUND");
                Files.write(work.resolve(outputId + output.getKey()), bytes, StandardOpenOption.CREATE_NEW);
            }
            result("selected_context_model:" + context.id(), "model_only_success", metadata + ";request_start=" + firstRequest + ";request_end=" + requests.size() + ";repository_start=" + firstRepository + ";repository_end=" + repositoryIds.size() + ";dependencies=" + dependencies.size() + ";problems=" + problems.size() + ";not descriptor/project build equivalence");
        }
        Files.write(work.resolve("resolver-requests.txt"), requests, StandardCharsets.UTF_8);
        Files.write(work.resolve("ignored-repository-ids.txt"), repositoryIds, StandardCharsets.UTF_8);
        result("summary", "bounded_complete", "control_assertions=" + passed + ";model_inputs=" + pins.size() + ";no CLI/plugin/processor/extension/provider/augmentation");
    }
}
