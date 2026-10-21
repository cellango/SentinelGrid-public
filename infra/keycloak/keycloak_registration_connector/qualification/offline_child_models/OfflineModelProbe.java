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
                .setValidationLevel(ModelBuildingRequest.VALIDATION_LEVEL_MAVEN_3_1);
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
        List<String> targets = List.of(
            "com.apicatalog:titanium-json-ld:1.3.3",
            "com.ethlo.time:itu:1.14.0",
            "com.fasterxml.jackson.core:jackson-annotations:2.21",
            "com.fasterxml.jackson.core:jackson-annotations:2.22",
            "com.fasterxml.jackson.core:jackson-core:2.21.7",
            "com.fasterxml.jackson.core:jackson-core:2.22.2",
            "com.fasterxml.jackson.core:jackson-databind:2.21.7",
            "com.fasterxml.jackson.core:jackson-databind:2.22.2",
            "com.fasterxml.jackson.dataformat:jackson-dataformat-cbor:2.21.7",
            "com.fasterxml.jackson.dataformat:jackson-dataformat-xml:2.21.7",
            "com.fasterxml.jackson.dataformat:jackson-dataformat-yaml:2.21.7",
            "com.fasterxml.jackson.dataformat:jackson-dataformat-yaml:2.22.2",
            "com.fasterxml.jackson.datatype:jackson-datatype-jdk8:2.21.7",
            "com.fasterxml.jackson.datatype:jackson-datatype-jdk8:2.22.2",
            "com.fasterxml.jackson.jakarta.rs:jackson-jakarta-rs-yaml-provider:2.21.7",
            "com.fasterxml.woodstox:woodstox-core:7.1.1",
            "com.github.hypfvieh:dbus-java-transport-native-unixsocket:5.2.0",
            "com.github.package-url:packageurl-java:1.5.0",
            "com.github.ua-parser:uap-java:1.6.1",
            "com.google.guava:guava:33.6.0-jre",
            "com.google.zxing:core:3.4.0",
            "com.google.zxing:javase:3.4.0",
            "com.googlecode.owasp-java-html-sanitizer:java10-shim:20260101.1",
            "com.googlecode.owasp-java-html-sanitizer:java8-shim:20260101.1",
            "com.googlecode.owasp-java-html-sanitizer:owasp-java-html-sanitizer:20260101.1",
            "com.networknt:json-schema-validator:2.0.1",
            "com.sun.xml.messaging.saaj:saaj-impl:2.0.1",
            "com.webauthn4j:webauthn4j-core:0.30.3.RELEASE",
            "com.webauthn4j:webauthn4j-util:0.30.3.RELEASE",
            "commons-codec:commons-codec:1.22.1",
            "commons-io:commons-io:2.22.0",
            "info.picocli:picocli:4.7.7",
            "io.fabric8:maven-model-helper:41",
            "io.mvnpm:importmap:1.0.11",
            "io.opentelemetry.instrumentation:opentelemetry-apache-httpclient-4.3:2.28.1-alpha",
            "io.opentelemetry.instrumentation:opentelemetry-jdbc:2.28.1-alpha",
            "io.quarkus.gizmo:gizmo2:2.1.1",
            "io.quarkus.gizmo:gizmo:1.10.1",
            "io.quarkus.qute:qute-core:3.40.1",
            "io.quarkus:quarkus-agroal:3.40.1",
            "io.quarkus:quarkus-analytics-common:3.40.1",
            "io.quarkus:quarkus-arc-deployment:3.40.1",
            "io.quarkus:quarkus-bootstrap-app-model:3.40.1",
            "io.quarkus:quarkus-bootstrap-core:3.40.1",
            "io.quarkus:quarkus-bootstrap-json:3.40.1",
            "io.quarkus:quarkus-bootstrap-maven-resolver:3.40.1",
            "io.quarkus:quarkus-bootstrap-maven4-resolver:3.40.1",
            "io.quarkus:quarkus-bootstrap-runner:3.40.1",
            "io.quarkus:quarkus-builder:3.40.1",
            "io.quarkus:quarkus-class-change-agent:3.40.1",
            "io.quarkus:quarkus-classloader-commons:3.40.1",
            "io.quarkus:quarkus-core-deployment:3.40.1",
            "io.quarkus:quarkus-core:3.40.1",
            "io.quarkus:quarkus-cyclonedx-generator:3.40.1",
            "io.quarkus:quarkus-development-mode-spi:3.40.1",
            "io.quarkus:quarkus-devtools-base-codestarts:3.40.1",
            "io.quarkus:quarkus-devtools-codestarts:3.40.1",
            "io.quarkus:quarkus-devtools-common:3.40.1",
            "io.quarkus:quarkus-devtools-message-writer:3.40.1",
            "io.quarkus:quarkus-devtools-registry-client:3.40.1",
            "io.quarkus:quarkus-extension-maven-plugin:3.40.1",
            "io.quarkus:quarkus-extension-processor:3.40.1",
            "io.quarkus:quarkus-fs-util:1.4.2",
            "io.quarkus:quarkus-hibernate-orm-deployment:3.40.1",
            "io.quarkus:quarkus-hibernate-orm:3.40.1",
            "io.quarkus:quarkus-hibernate-validator-deployment:3.40.1",
            "io.quarkus:quarkus-hibernate-validator-spi:3.40.1",
            "io.quarkus:quarkus-hibernate-validator:3.40.1",
            "io.quarkus:quarkus-jdbc-h2-deployment:3.40.1",
            "io.quarkus:quarkus-jdbc-h2:3.40.1",
            "io.quarkus:quarkus-jdbc-mariadb-deployment:3.40.1",
            "io.quarkus:quarkus-jdbc-mariadb:3.40.1",
            "io.quarkus:quarkus-jdbc-mssql-deployment:3.40.1",
            "io.quarkus:quarkus-jdbc-mssql:3.40.1",
            "io.quarkus:quarkus-jdbc-mysql-deployment:3.40.1",
            "io.quarkus:quarkus-jdbc-mysql:3.40.1",
            "io.quarkus:quarkus-jdbc-oracle-deployment:3.40.1",
            "io.quarkus:quarkus-jdbc-oracle:3.40.1",
            "io.quarkus:quarkus-jdbc-postgresql-deployment:3.40.1",
            "io.quarkus:quarkus-jdbc-postgresql:3.40.1",
            "io.quarkus:quarkus-junit5-internal:3.40.1",
            "io.quarkus:quarkus-junit5-mockito:3.40.1",
            "io.quarkus:quarkus-logging-json-deployment:3.40.1",
            "io.quarkus:quarkus-logging-json:3.40.1",
            "io.quarkus:quarkus-maven-plugin:3.40.1",
            "io.quarkus:quarkus-micrometer-deployment:3.40.1",
            "io.quarkus:quarkus-micrometer-opentelemetry-deployment:3.40.1",
            "io.quarkus:quarkus-micrometer-opentelemetry:3.40.1",
            "io.quarkus:quarkus-micrometer-registry-prometheus-deployment:3.40.1",
            "io.quarkus:quarkus-micrometer-registry-prometheus:3.40.1",
            "io.quarkus:quarkus-micrometer:3.40.1",
            "io.quarkus:quarkus-opentelemetry-deployment:3.40.1",
            "io.quarkus:quarkus-opentelemetry:3.40.1",
            "io.quarkus:quarkus-project-core-extension-codestarts:3.40.1",
            "io.quarkus:quarkus-rest-deployment:3.40.1",
            "io.quarkus:quarkus-rest-jackson-deployment:3.40.1",
            "io.quarkus:quarkus-rest-jackson:3.40.1",
            "io.quarkus:quarkus-rest:3.40.1",
            "io.quarkus:quarkus-smallrye-health-deployment:3.40.1",
            "io.quarkus:quarkus-smallrye-health:3.40.1",
            "io.quarkus:quarkus-smallrye-openapi-deployment:3.40.1",
            "io.quarkus:quarkus-smallrye-openapi:3.40.1",
            "io.quarkus:quarkus-swagger-ui-deployment:3.40.1",
            "io.quarkus:quarkus-swagger-ui:3.40.1",
            "io.quarkus:quarkus-value-registry:3.40.1",
            "io.quarkus:quarkus-vertx-http:3.40.1",
            "io.quarkus:quarkus-vertx:3.40.1",
            "io.rest-assured:rest-assured:6.0.1",
            "io.setl:rdf-urdna:1.1",
            "io.smallrye.beanbag:smallrye-beanbag-maven:1.6.1",
            "io.smallrye.beanbag:smallrye-beanbag-sisu:1.6.1",
            "io.smallrye.beanbag:smallrye-beanbag:1.6.1",
            "io.smallrye.classfile:jdk-classfile-backport:26",
            "io.smallrye.common:smallrye-common-annotation:2.19.0",
            "io.smallrye.common:smallrye-common-classloader:2.19.0",
            "io.smallrye.common:smallrye-common-constraint:2.19.0",
            "io.smallrye.common:smallrye-common-cpu:2.19.0",
            "io.smallrye.common:smallrye-common-expression:2.19.0",
            "io.smallrye.common:smallrye-common-function:2.19.0",
            "io.smallrye.common:smallrye-common-io:2.19.0",
            "io.smallrye.common:smallrye-common-net:2.19.0",
            "io.smallrye.common:smallrye-common-os:2.19.0",
            "io.smallrye.common:smallrye-common-process:2.19.0",
            "io.smallrye.common:smallrye-common-ref:2.19.0",
            "io.smallrye.common:smallrye-common-resource:2.19.0",
            "io.smallrye.common:smallrye-common-search:2.19.0",
            "io.smallrye.common:smallrye-common-version:2.19.0",
            "io.smallrye.config:smallrye-config-common:3.17.2",
            "io.smallrye.config:smallrye-config-core:3.17.2",
            "io.smallrye.config:smallrye-config-source-keystore:3.17.2",
            "io.smallrye.config:smallrye-config:3.17.2",
            "io.smallrye.reactive:mutiny:3.3.0",
            "io.smallrye:jandex-gizmo2:3.6.0",
            "io.smallrye:jandex:3.6.0",
            "io.vertx:vertx-web-client:4.5.34",
            "jakarta.annotation:jakarta.annotation-api:3.0.0",
            "jakarta.el:jakarta.el-api:6.0.0",
            "jakarta.el:jakarta.el-api:6.0.1",
            "jakarta.enterprise:jakarta.enterprise.cdi-api:4.1.0",
            "jakarta.enterprise:jakarta.enterprise.lang-model:4.1.0",
            "jakarta.inject:jakarta.inject-api:2.0.1",
            "jakarta.interceptor:jakarta.interceptor-api:2.2.0",
            "jakarta.json:jakarta.json-api:2.1.3",
            "jakarta.mail:jakarta.mail-api:2.1.1",
            "jakarta.transaction:jakarta.transaction-api:2.0.1",
            "jakarta.xml.bind:jakarta.xml.bind-api:4.0.5",
            "jakarta.xml.soap:jakarta.xml.soap-api:3.0.0",
            "javax.inject:javax.inject:1",
            "junit:junit:4.13.2",
            "net.bytebuddy:byte-buddy-agent:1.18.8",
            "net.java.dev.jna:jna:5.8.0",
            "org.aesh:aesh:3.18.2",
            "org.aesh:readline-api:3.18.1",
            "org.aesh:readline:3.18.1",
            "org.aesh:terminal-api:3.18.1",
            "org.aesh:terminal-detect:3.18.1",
            "org.aesh:terminal-tty:3.18.1",
            "org.apache.commons:commons-collections4:4.5.0",
            "org.apache.commons:commons-compress:1.28.0",
            "org.apache.commons:commons-lang3:3.20.0",
            "org.apache.httpcomponents:httpclient:4.5.14",
            "org.apache.httpcomponents:httpcore:4.4.16",
            "org.apache.maven.extensions:maven-build-cache-extension:1.2.0",
            "org.apache.maven.plugin-tools:maven-plugin-annotations:3.15.1",
            "org.apache.maven.plugins:maven-compiler-plugin:3.13.0",
            "org.apache.maven.plugins:maven-failsafe-plugin:2.22.2",
            "org.apache.maven.plugins:maven-surefire-plugin:3.5.6",
            "org.apache.maven:maven-api-meta:4.0.0-alpha-7",
            "org.apache.maven:maven-api-xml:4.0.0-alpha-7",
            "org.apache.maven:maven-xml-impl:4.0.0-alpha-7",
            "org.apache.santuario:xmlsec:3.0.6",
            "org.apiguardian:apiguardian-api:1.1.2",
            "org.codehaus.plexus:plexus-cipher:2.0",
            "org.codehaus.plexus:plexus-interpolation:1.26",
            "org.codehaus.plexus:plexus-sec-dispatcher:2.0",
            "org.codehaus.plexus:plexus-utils:3.6.1",
            "org.codehaus.plexus:plexus-xml:4.0.2",
            "org.codehaus.woodstox:stax2-api:4.2.2",
            "org.codejive:java-properties:0.0.7",
            "org.crac:crac:1.5.0",
            "org.cyclonedx:cyclonedx-core-java:12.2.0",
            "org.eclipse.angus:angus-mail:2.0.5",
            "org.eclipse.microprofile.config:microprofile-config-api:3.1.1",
            "org.eclipse.parsson:parsson:1.1.7",
            "org.eclipse.parsson:parsson:1.1.9",
            "org.eclipse.sisu:org.eclipse.sisu.inject:1.0.1",
            "org.eclipse.sisu:org.eclipse.sisu.plexus:1.0.1",
            "org.freemarker:freemarker:2.3.35",
            "org.graalvm.sdk:nativeimage:25.0.4.1",
            "org.graalvm.sdk:word:25.0.4.1",
            "org.hamcrest:hamcrest:2.2",
            "org.hibernate.orm:hibernate-community-dialects:7.4.9.Final",
            "org.infinispan:infinispan-api:16.0.15",
            "org.infinispan:infinispan-cachestore-remote:16.0.15",
            "org.infinispan:infinispan-commons:16.0.15",
            "org.infinispan:infinispan-component-annotations:16.0.15",
            "org.infinispan:infinispan-core:16.0.15",
            "org.jboss.logging:commons-logging-jboss-logging:2.0.0.Final",
            "org.jboss.logging:jboss-logging:3.6.3.Final",
            "org.jboss.logmanager:jboss-logmanager:3.2.2.Final",
            "org.jboss.slf4j:slf4j-jboss-logmanager:1.1.0.Final",
            "org.jboss.slf4j:slf4j-jboss-logmanager:2.0.2.Final",
            "org.jboss.threads:jboss-threads:3.9.2",
            "org.jctools:jctools-core:4.0.5",
            "org.jdom:jdom2:2.0.6.1",
            "org.jspecify:jspecify:1.0.0",
            "org.junit.jupiter:junit-jupiter:6.1.3",
            "org.junit.platform:junit-platform-commons:6.1.3",
            "org.junit.platform:junit-platform-engine:6.1.3",
            "org.junit.platform:junit-platform-launcher:6.1.3",
            "org.keycloak:keycloak-account-ui:26.8.1",
            "org.keycloak:keycloak-admin-ui:26.8.1",
            "org.keycloak:keycloak-admin-v2-api:26.8.1",
            "org.keycloak:keycloak-admin-v2-services:26.8.1",
            "org.keycloak:keycloak-authz-policy-common:26.8.1",
            "org.keycloak:keycloak-authzen-services:26.8.1",
            "org.keycloak:keycloak-common:26.8.1",
            "org.keycloak:keycloak-config-api:26.8.1",
            "org.keycloak:keycloak-core:26.8.1",
            "org.keycloak:keycloak-crypto-default:26.8.1",
            "org.keycloak:keycloak-crypto-fips1402:26.8.1",
            "org.keycloak:keycloak-ipatuura-federation:26.8.1",
            "org.keycloak:keycloak-kerberos-federation:26.8.1",
            "org.keycloak:keycloak-ldap-federation:26.8.1",
            "org.keycloak:keycloak-model-infinispan:26.8.1",
            "org.keycloak:keycloak-model-jpa:26.8.1",
            "org.keycloak:keycloak-model-storage-private:26.8.1",
            "org.keycloak:keycloak-model-storage-services:26.8.1",
            "org.keycloak:keycloak-model-storage:26.8.1",
            "org.keycloak:keycloak-parent:26.8.1",
            "org.keycloak:keycloak-quarkus-parent:26.8.1",
            "org.keycloak:keycloak-quarkus-server-app:26.8.1",
            "org.keycloak:keycloak-quarkus-server-deployment:26.8.1",
            "org.keycloak:keycloak-quarkus-server:26.8.1",
            "org.keycloak:keycloak-rest-admin-ui-ext:26.8.1",
            "org.keycloak:keycloak-saml-core-public:26.8.1",
            "org.keycloak:keycloak-saml-core:26.8.1",
            "org.keycloak:keycloak-scim-core:26.8.1",
            "org.keycloak:keycloak-scim-model:26.8.1",
            "org.keycloak:keycloak-scim-services:26.8.1",
            "org.keycloak:keycloak-server-spi-private:26.8.1",
            "org.keycloak:keycloak-server-spi:26.8.1",
            "org.keycloak:keycloak-services:26.8.1",
            "org.keycloak:keycloak-ssf-core:26.8.1",
            "org.keycloak:keycloak-ssf-services:26.8.1",
            "org.keycloak:keycloak-ssf-transmitter:26.8.1",
            "org.keycloak:keycloak-sssd-federation:26.8.1",
            "org.keycloak:keycloak-themes-vendor:26.8.1",
            "org.keycloak:keycloak-themes:26.8.1",
            "org.liquibase:liquibase-core:4.33.0",
            "org.openjdk.nashorn:nashorn-core:15.4",
            "org.opentest4j:opentest4j:1.3.0",
            "org.ow2.asm:asm-analysis:9.10.1",
            "org.ow2.asm:asm-commons:9.10.1",
            "org.ow2.asm:asm-tree:9.10.1",
            "org.ow2.asm:asm-util:9.10.1",
            "org.ow2.asm:asm:9.10.1",
            "org.slf4j:slf4j-api:2.0.18",
            "org.snakeyaml:snakeyaml-engine:2.6",
            "org.twdata.maven:mojo-executor:2.4.0",
            "org.twitter4j:twitter4j-core:4.1.2",
            "org.wildfly.common:wildfly-common:2.0.1",
            "org.yaml:snakeyaml:2.0",
            "org.yaml:snakeyaml:2.5",
            "org.yaml:snakeyaml:2.6");
        require(targets.size() == 265 && new HashSet<>(targets).size() == 265, "TARGET_COUNT");
        long totalOutputBytes = 0;
        for (int index = 0; index < targets.size(); index++) {
            String coordinate = targets.get(index);
            int firstRequest = requests.size(), firstRepository = repositoryIds.size();
            String outputId = String.format(Locale.ROOT, "child-%04d", index);
            ModelBuildingResult built;
            try { built = model(coordinate, Set.of("crypto-default", "upstream-adapters")); }
            catch (ModelBuildingException failure) {
                result("selected_child_model:" + coordinate, "NO_GO", "output=" + outputId + ";request_start=" + firstRequest + ";request_end=" + requests.size() + ";repository_start=" + firstRepository + ";repository_end=" + repositoryIds.size() + ";failure=" + failure); continue;
            }
            Model effective = built.getEffectiveModel();
            require(coordinate.equals(effective.getGroupId() + ":" + effective.getArtifactId() + ":" + effective.getVersion()), "EFFECTIVE_IDENTITY");
            List<String> dependencies = new ArrayList<>();
            for (Dependency dep : effective.getDependencies()) dependencies.add(dep.getGroupId() + ":" + dep.getArtifactId() + ":" + dep.getVersion() + ":" + dep.getType() + ":" + dep.getClassifier() + ":" + dep.getScope() + ":optional=" + dep.isOptional() + ":exclusions=" + dep.getExclusions().size());
            StringWriter xml = new StringWriter();
            new org.apache.maven.model.io.xpp3.MavenXpp3Writer().write(xml, effective);
            List<String> provenance = new ArrayList<>();
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
            for (Map.Entry<String, String> output : outputs.entrySet()) {
                byte[] bytes = output.getValue().getBytes(StandardCharsets.UTF_8);
                require(bytes.length <= 8 * 1024 * 1024, "TARGET_OUTPUT_BOUND");
                totalOutputBytes += bytes.length;
                require(totalOutputBytes <= 256L * 1024 * 1024, "TOTAL_OUTPUT_BOUND");
                Files.write(work.resolve(outputId + output.getKey()), bytes, StandardOpenOption.CREATE_NEW);
            }
            result("selected_child_model:" + coordinate, "model_only_success", "output=" + outputId + ";request_start=" + firstRequest + ";request_end=" + requests.size() + ";repository_start=" + firstRepository + ";repository_end=" + repositoryIds.size() + ";dependencies=" + dependencies.size() + ";profiles=explicit-crypto-default+upstream-adapters;plugins_not_processed;not binary/provider graph");
        }
        Files.write(work.resolve("resolver-requests.txt"), requests, StandardCharsets.UTF_8);
        Files.write(work.resolve("ignored-repository-ids.txt"), repositoryIds, StandardCharsets.UTF_8);
        result("summary", "bounded_complete", "control_assertions=" + passed + ";model_inputs=" + pins.size() + ";no CLI/plugin/processor/extension/provider/augmentation");
    }
}
