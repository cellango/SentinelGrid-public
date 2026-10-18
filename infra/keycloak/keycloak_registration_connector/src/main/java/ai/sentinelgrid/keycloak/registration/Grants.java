// SPDX-License-Identifier: Apache-2.0
package ai.sentinelgrid.keycloak.registration;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Immutable operator configuration. Never read grant configuration from an HTTP request. */
final class Grants {
  static final ObjectMapper JSON =
      new ObjectMapper()
          .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
          .enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
  static final Set<String> FIELDS =
      Set.of(
          "issuer",
          "realm_id",
          "iam_audience",
          "management_client_id",
          "management_subject_id",
          "client_uuid",
          "client_id",
          "subject_id",
          "tenant_id");

  record Grant(
      String issuer,
      String realmId,
      String iamAudience,
      String managementClientId,
      String managementSubjectId,
      String clientUuid,
      String clientId,
      String subjectId,
      String tenantId) {}

  final boolean enabled;
  final long version;
  final String sha256;
  final List<Grant> rows;

  Grants(boolean enabled, String input) {
    try {
      if (input == null || input.getBytes(StandardCharsets.UTF_8).length > 65536)
        throw new IllegalArgumentException();
      JsonNode root = JSON.readTree(input);
      exact(root, Set.of("version", "grants"));
      JsonNode revision = root.get("version"), values = root.get("grants");
      if (!revision.isIntegralNumber()
          || !revision.canConvertToLong()
          || revision.longValue() < 1
          || !values.isArray()
          || values.size() > 128) throw new IllegalArgumentException();
      version = revision.longValue();
      List<Grant> parsed = new ArrayList<>();
      Set<String> owners = new HashSet<>();
      for (JsonNode row : values) {
        exact(row, FIELDS);
        String issuer = text(row, "issuer");
        URI u = URI.create(issuer);
        if (!"https".equals(u.getScheme())
            || u.getHost() == null
            || u.getRawUserInfo() != null
            || u.getRawQuery() != null
            || u.getRawFragment() != null
            || u.getPort() == 0
            || issuer.contains("%")
            || issuer.contains("\\")
            || u.getPath().contains("//")
            || Arrays.stream(u.getPath().split("/")).anyMatch(p -> p.equals(".") || p.equals(".."))
            || !u.getPath().matches(".*/realms/[A-Za-z0-9][A-Za-z0-9_.-]{0,127}"))
          throw new IllegalArgumentException();
        String realm = text(row, "realm_id"), audience = identifier(text(row, "iam_audience"));
        String management = identifier(text(row, "management_client_id")),
            subject = uuid(text(row, "management_subject_id"));
        String clientUuid = uuid(text(row, "client_uuid")),
            client = identifier(text(row, "client_id"));
        String targetSubject = uuid(text(row, "subject_id")), tenant = uuid(text(row, "tenant_id"));
        if (realm.length() > 128
            || audience.equals(AssociationResource.AUDIENCE)
            || management.equals(client)
            || subject.equals(targetSubject)) throw new IllegalArgumentException();
        Grant grant =
            new Grant(
                issuer,
                realm,
                audience,
                management,
                subject,
                clientUuid,
                client,
                targetSubject,
                tenant);
        // One exact target for this management identity/realm; conflicting duplicate ownership
        // denies config.
        if (!owners.add(issuer + "|" + realm + "|" + management + "|" + subject + "|" + clientUuid))
          throw new IllegalArgumentException();
        parsed.add(grant);
      }
      rows = List.copyOf(parsed);
      this.enabled = enabled;
      sha256 =
          HexFormat.of()
              .formatHex(
                  MessageDigest.getInstance("SHA-256")
                      .digest(input.getBytes(StandardCharsets.UTF_8)));
    } catch (Exception e) {
      throw new IllegalArgumentException("Invalid owned association grants");
    }
  }

  static String text(JsonNode node, String name) {
    JsonNode v = node.get(name);
    if (v == null
        || !v.isTextual()
        || v.textValue().isEmpty()
        || v.textValue().length() > 2048
        || v.textValue().chars().anyMatch(c -> c < 33 || c > 126))
      throw new IllegalArgumentException();
    return v.textValue();
  }

  static String uuid(String v) {
    UUID p = UUID.fromString(v);
    if (!p.toString().equals(v) || p.equals(new UUID(0, 0))) throw new IllegalArgumentException();
    return v;
  }

  static String identifier(String v) {
    if (!v.matches("[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")) throw new IllegalArgumentException();
    return v;
  }

  static void exact(JsonNode node, Set<String> expected) {
    if (node == null || !node.isObject()) throw new IllegalArgumentException();
    Set<String> actual = new HashSet<>();
    node.fieldNames().forEachRemaining(actual::add);
    if (!actual.equals(expected)) throw new IllegalArgumentException();
  }
}
