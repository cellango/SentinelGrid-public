# Production Release And Deploy

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Purpose

Release and deploy the launch-scope SentinelGrid services to ECR and EKS with a repeatable, auditable path.

## Canonical Launch Services

- `frontend` from `frontend/Dockerfile`
- `api-gateway` from `backend/services/api_gateway/Dockerfile`
- `iam-agent` from `backend/agents/iam_agent/Dockerfile`
- `model-gateway` from `backend/services/model_gateway/Dockerfile`
- `orchestrator` from `backend/services/orchestrator/Dockerfile`
- `siem-agent` from `backend/agents/siem_agent/Dockerfile`

## Important Repo Truth

- The canonical SIEM runtime for launch is `backend/agents/siem_agent/`.
- `backend/services/siem_agent/` still exists in historical docs and should not be used as the production deploy target.

## GitHub Environment Prerequisites

Set these per GitHub Environment (`dev`, `stage`, `prod`):

- Secret: `AWS_ECR_DEPLOY_ROLE_ARN`
- Variable: `AWS_REGION`
- Variable: `ECR_REGISTRY`
- Variable: `EKS_CLUSTER`
- Variable: `K8S_NAMESPACE`
- Variable: `FRONTEND_HOST`
- Variable: `API_HOST`
- Variable: `IAM_HOST`
- Variable: `FRONTEND_CERTIFICATE_ARN`
- Variable: `API_CERTIFICATE_ARN`
- Variable: `IAM_CERTIFICATE_ARN`
- Optional variable: `NEXT_PUBLIC_API_BASE`
- Optional variable: `NEXT_PUBLIC_API_URL`
- Optional variable: `NEXT_PUBLIC_IAM_AGENT_URL`

`ECR_REGISTRY` should include the image namespace prefix used by Helm, for example:

```text
123456789012.dkr.ecr.us-east-1.amazonaws.com/sentinelgrid
```

`FRONTEND_CERTIFICATE_ARN`, `API_CERTIFICATE_ARN`, and `IAM_CERTIFICATE_ARN` must be ACM certificate ARNs for the exact public hostnames used by each ingress.

## Public Ingress TLS Contract

Launch-scope public ingress is HTTPS-only by default.

- `frontend`: public ALB listener `443`, backend protocol `HTTPS`, health check `GET /`
- `api-gateway`: public ALB listener `443`, backend protocol `HTTP`, health check `GET /ready`
- `iam-agent`: restricted public ALB listener `443`, backend protocol `HTTP`, health check `GET /health`

Certificate management expectations:

- every public ingress release must set `ingress.alb.certificateArn`
- the deploy workflow injects the certificate ARN from the GitHub Environment variables above
- `charts/common-service/templates/ingress.yaml` fails the Helm render if a service marks `ingress.alb.requireCertificate=true` without a certificate ARN

HTTP-to-HTTPS redirect is not part of the default launch posture because the public listeners are HTTPS-only. If a transitional edge must keep port `80`, explicitly set:

- `ingress.alb.listenPorts='[{\"HTTP\":80},{\"HTTPS\":443}]'`
- `ingress.alb.sslRedirect='443'`

Do not use a plain-HTTP listener as the primary production path.

## Release Flow

1. Freeze the release branch and confirm the current phase closeout docs match the code.
2. Run the required CI and targeted smoke tests before invoking deployment.
3. Run `.github/workflows/build-push-deploy.yml`.
4. Choose the environment and image tag. Leave `image_tag` empty to use the current commit SHA.
5. Use `deploy=false` if you only want fresh ECR images.
6. Use `deploy=true` for a full EKS rollout.
7. Confirm Helm rollouts succeed for all six launch services.

## What The Workflow Does

- lints schema-only migrations with `scripts/lint_migrations_schema_only.sh`
- rebuilds and pushes shared base images
- builds and pushes the six launch-scope service images
- deploys them through `charts/common-service`
- waits for each deployment rollout to finish before continuing

## Required Pre-Deploy Checks

- Database migration plan reviewed and, if needed, executed per `database_migrations_and_bootstrap.md`
- Fresh backups completed per `backup_restore_and_dr.md`
- No unresolved P0 production risks for the target environment
- `bash scripts/phase6/run-preaudit-dry-run.sh` passes if this rollout is intended to seed or preserve the current release-candidate / re-audit baseline
- `bash scripts/phase6/verify-launch-scope-observability.sh` passes against the current repo state
- Current environment variables and secrets rotated or validated
- Required launch runtime secrets exist in the target namespace:
  - `api-gateway-runtime`
  - `iam-agent-runtime`
  - `model-gateway-runtime`
  - `orchestrator-runtime`
  - `siem-agent-runtime`
- Those runtime secrets contain non-placeholder values for the launch-critical backing-service and auth settings:
  - database URLs
  - Redis URLs
  - internal service tokens
  - external Keycloak / Vault / OpenSearch URLs where applicable

## Post-Deploy Verification

Run these checks immediately after rollout:

- `kubectl get pods -n <namespace>`
- `kubectl get ingress -n <namespace>`
- `kubectl get networkpolicy -n <namespace>`
- `kubectl get secret api-gateway-runtime iam-agent-runtime model-gateway-runtime orchestrator-runtime siem-agent-runtime -n <namespace>`
- `kubectl describe ingress api-gateway -n <namespace>`
- `kubectl describe ingress frontend -n <namespace>`
- `kubectl describe ingress iam-agent -n <namespace>`
- `kubectl describe networkpolicy frontend -n <namespace>`
- `kubectl describe networkpolicy api-gateway -n <namespace>`
- `kubectl describe networkpolicy model-gateway -n <namespace>`
- `kubectl get deploy frontend api-gateway iam-agent model-gateway orchestrator siem-agent -n <namespace> -o yaml`
- `kubectl get deploy frontend api-gateway iam-agent model-gateway orchestrator siem-agent -n <namespace> -o jsonpath='{range .items[*]}{.metadata.name}{": l="}{.spec.template.spec.containers[0].livenessProbe.httpGet.path}{", r="}{.spec.template.spec.containers[0].readinessProbe.httpGet.path}{", s="}{.spec.template.spec.containers[0].startupProbe.httpGet.path}{"\n"}{end}'`
- `curl -fsS https://<frontend-host>/`
- `curl -fsS https://<api-host>/health`
- `curl -fsS https://<api-host>/ready`

Confirm on the described ingresses:

- `alb.ingress.kubernetes.io/listen-ports` resolves to `443`-based HTTPS listeners for the public releases
- `alb.ingress.kubernetes.io/certificate-arn` is populated
- `alb.ingress.kubernetes.io/healthcheck-path` matches the release contract above

Confirm on the described network policies:

- public entry points expose ingress only on the declared service port
- internal services such as `model-gateway` have no public ingress resource in `kubectl get ingress -n <namespace>`
- `frontend`, `api-gateway`, `iam-agent`, `model-gateway`, `orchestrator`, and `siem-agent` each show explicit ingress and egress policy structure where expected
- internal east-west traffic is allowlisted by named dependencies rather than namespace-wide trust

Confirm on the rendered deployment specs:

- launch-scope workloads set `runAsNonRoot: true`
- pod specs carry explicit runtime UID and GID plus `seccompProfile.type: RuntimeDefault`
- container specs set `allowPrivilegeEscalation: false`
- container specs set `readOnlyRootFilesystem: true`
- launch-scope workloads keep explicit `livenessProbe`, `readinessProbe`, and `startupProbe`
- writable mounts are explicit:
  - `/tmp` for the standard launch services
  - `/tmp` and `/models` for `model-gateway`

Then verify operator flows manually:

- login and refresh
- dashboard load
- Now queue load
- alerts page load
- incidents page load
- onboarding status load

## Rollback

If the release is unhealthy:

1. Stop new deploys.
2. Identify the failing release with `kubectl rollout status` and `/ready`.
3. Roll back the specific Helm release:

```bash
helm rollback api-gateway 1 -n sg-core
helm rollback frontend 1 -n sg-core
```

4. Re-run post-deploy verification.
5. If schema changes were included, follow the rollback notes in `database_migrations_and_bootstrap.md`.

For drill evidence, prefer the wrapper:

```bash
./infra/shared/scripts/run-release-rollback-drill.sh \
  --release api-gateway \
  --revision 1 \
  --namespace sg-core \
  --ready-url https://api.example.com/ready \
  --mode live
```

The wrapper stores evidence under:

```text
artifacts/drills/rollback/<YYYY-MM-DD>/<run-id>/
```

Use `--mode plan` to stage the drill before cluster execution.

Recommended rollback drill timebox for the narrowed launch scope:

- Helm rollback and readiness verification: 15 minutes

Example with explicit timebox:

```bash
./infra/shared/scripts/run-release-rollback-drill.sh \
  --release api-gateway \
  --revision 1 \
  --namespace sg-core \
  --ready-url https://api.example.com/ready \
  --mode live \
  --timebox-minutes 15
```

The wrapper now records:

- `result.json`
- `summary.md`
- `operator-actions.md`

including measured duration and whether the rollback stayed inside the declared timebox.

## Evidence To Save

- workflow run URL
- exact image tag
- Helm revision numbers
- post-deploy `/ready` responses
- smoke-test result links or logs
- rollback timebox compliance from `result.json`
- `operator-actions.md`
- rollback drill evidence directory when `run-release-rollback-drill.sh` is used
