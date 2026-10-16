# DNS Naming Convention (SentinelGrid)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Goal: consistent, cert-friendly hostnames across environments, with minimal prefixes and no environment suffix baked into service names.

## Principles
- Single root zone: `sentinelgrid.ai` for both public and private records (split-horizon/private zones for internal-only services).
- Environment prefix on the **left**; prod is prefix-less:
  - Prod: `<service>.sentinelgrid.ai`
  - Non-prod: `<env>.<service>.sentinelgrid.ai` (e.g., `dev.vault.sentinelgrid.ai`, `stage.frontend.sentinelgrid.ai`)
- Service names stay environment-neutral (`vault`, `frontend`, `api`, `opensearch`, `keycloak`, `step-ca`); avoid `*-prod`.
- Certificates SANs must include the service FQDN(s) per environment and any internal aliases used by clients; avoid `localhost/127.0.0.1`.
- mTLS endpoints (e.g., Vault, step-ca) use the same hostnames; client certs reference those hosts.

## Patterns
- Core services (prod): `vault.sentinelgrid.ai`, `api.sentinelgrid.ai`, `frontend.sentinelgrid.ai`, `opensearch.sentinelgrid.ai`, `identity.sentinelgrid.ai` (Keycloak), `step-ca.sentinelgrid.ai`
- Core services (non-prod): `dev.vault.sentinelgrid.ai`, `dev.api.sentinelgrid.ai`, `dev.frontend.sentinelgrid.ai`, `dev.identity.sentinelgrid.ai`, etc. Same pattern for `stage.<service>.sentinelgrid.ai`.
- Tenant-facing entrypoints (if exposed): `<tenant>.api.sentinelgrid.ai` (prod) and `dev.<tenant>.api.sentinelgrid.ai` (non-prod) via CNAME to gateway/LB; keep internal control-plane on the service FQDNs above.
- Internal-only records: prefer split-horizon/private DNS for the same names; avoid tacking on “internal” unless policy requires a separate zone (e.g., `internal.sentinelgrid.ai`). If a separate private zone is mandated, mirror names as `<service>.internal.sentinelgrid.ai` / `dev.<service>.internal.sentinelgrid.ai`.

## Certificate guidance (EJBCA)
- Server cert SANs: include the service FQDN for the target env (e.g., `vault.sentinelgrid.ai`, `dev.vault.sentinelgrid.ai`) and the in-cluster/service alias if used (e.g., `vault` on Docker/k8s DNS). Do **not** include `localhost`.
- Client certs for automation/health (e.g., `automation.crt`): CN/OU marking automation, EKU=clientAuth; clients connect via the FQDN above.
- Use separate profiles for server vs. client; short validity with automation for renewal.

## Records & resolution
- A/AAAA or CNAME to the appropriate LB/ingress per env.
- Split-horizon DNS: internal resolvers return private IPs; external resolvers return public/none as appropriate.
- Avoid embedding ports in names; use standard ports or LB listeners.

## Migration notes
- Rename `vault-prod` service references to `vault` and point clients to `vault.sentinelgrid.ai` (prod) / `dev.vault.sentinelgrid.ai` (non-prod); update cert SANs accordingly.
- Update health checks and mTLS clients to use the FQDN + client cert, not `localhost`.
- Rebrand Keycloak hostnames to identity: use `identity.sentinelgrid.ai` (prod) and `dev.identity.sentinelgrid.ai` (non-prod) in DNS, SANs, and client configs.
