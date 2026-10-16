# Phase 3 Slice 3C Runtime Hardening Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 17, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the launch-scope runtime hardening gap so the narrowed launch services run as non-root, the shared chart applies pod and container security controls at the correct Kubernetes levels, and writable filesystem access is reduced to explicit mounts instead of implicit root filesystem writes.

## Scope Closed In This Slice

- correct separation of pod-level and container-level security contexts in the shared deployment chart
- non-root runtime enforcement for the narrowed launch Helm releases
- launch-scope runtime baseline for:
  - `runAsNonRoot`
  - explicit `runAsUser` and `runAsGroup`
  - `fsGroup`
  - `seccompProfile.type: RuntimeDefault`
  - `allowPrivilegeEscalation: false`
  - `readOnlyRootFilesystem: true`
  - dropped Linux capabilities
- explicit writable mounts for the narrowed launch path:
  - `/tmp` for `frontend`, `api-gateway`, `iam-agent`, `orchestrator`, and `siem-agent`
  - `/tmp` and `/models` for `model-gateway`
- non-root runtime closure for the launch-critical Dockerfiles called out in the implementation plan
- runbook verification steps for confirming runtime hardening on deployed pods

## Code And Config Areas Closed

- `frontend/Dockerfile`
- `backend/services/api_gateway/Dockerfile`
- `backend/services/orchestrator/Dockerfile`
- `backend/agents/iam_agent/Dockerfile`
- `charts/common-service/templates/deployment.yaml`
- `charts/common-service/values.yaml`
- `charts/values/frontend.yaml`
- `charts/values/api-gateway.yaml`
- `charts/values/iam-agent.yaml`
- `charts/values/model-gateway.yaml`
- `charts/values/orchestrator.yaml`
- `charts/values/siem-agent.yaml`
- `docs/archive/operations/production-release-and-deploy.md`

## What Changed

1. `charts/common-service/templates/deployment.yaml` now renders:
   - `podSecurityContext` at the pod spec level
   - `securityContext` at the container level
   The old behavior incorrectly attached `securityContext` only at the pod level, which made launch-scope container hardening unenforceable.
2. `charts/common-service/values.yaml` now documents the chart contract more clearly by distinguishing pod-level and container-level security context fields.
3. The narrowed launch Helm values for `frontend`, `api-gateway`, `iam-agent`, `model-gateway`, `orchestrator`, and `siem-agent` now declare a common runtime baseline:
   - non-root UID and GID
   - `fsGroup`
   - `seccompProfile.type: RuntimeDefault`
   - `allowPrivilegeEscalation: false`
   - `readOnlyRootFilesystem: true`
   - `capabilities.drop: [ALL]`
4. The narrowed launch values now mount only the writable paths required by the services:
   - `/tmp` for the standard app services
   - `/models` in `model-gateway` for runtime model and adapter storage
5. `frontend/Dockerfile` now supports a non-root runtime cleanly:
   - container runtime user is `nextjs`
   - nginx PID, logs, and temp paths move under `/tmp`
   - the startup path uses the built `next` binary directly rather than relying on `npm run start`
   - the container no longer depends on writing to `/var/log/nginx`, `/var/cache/nginx`, or `/run/nginx`
6. `backend/services/api_gateway/Dockerfile` and `backend/agents/iam_agent/Dockerfile` now use explicit root-only build steps and return to the base-image `sentinelgrid` user for runtime.
7. `backend/services/orchestrator/Dockerfile` now creates and runs as the `sentinelgrid` user instead of leaving the service on the default root user from `python:3.11-slim`.
8. `docs/archive/operations/production-release-and-deploy.md` now includes post-deploy pod-runtime checks so the hardened spec is verified in the cluster rather than assumed from Helm values alone.

## Verification Evidence

### Helm Render Evidence

- `helm template frontend charts/common-service -f charts/values/frontend.yaml --set-string image.repository=test/frontend --set-string image.tag=test --set-string 'ingress.hosts[0].host=app.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/frontend-test`
  - result: rendered deployment includes:
    - `runAsNonRoot: true`
    - `runAsUser: 1001`
    - `runAsGroup: 1001`
    - `fsGroup: 1001`
    - `seccompProfile.type: RuntimeDefault`
    - `allowPrivilegeEscalation: false`
    - `readOnlyRootFilesystem: true`
    - `/tmp` `emptyDir` mount

- `helm template api-gateway charts/common-service -f charts/values/api-gateway.yaml --set-string image.repository=test/api --set-string image.tag=test --set-string 'ingress.hosts[0].host=api.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/api-test`
  - result: rendered deployment includes the same runtime baseline with `runAsUser: 1000` and `/tmp` `emptyDir`

- `helm template iam-agent charts/common-service -f charts/values/iam-agent.yaml --set-string image.repository=test/iam --set-string image.tag=test --set-string 'ingress.hosts[0].host=auth.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/iam-test`
  - result: rendered deployment includes the same runtime baseline with `runAsUser: 1000` and `/tmp` `emptyDir`

- `helm template model-gateway charts/common-service -f charts/values/model-gateway.yaml --set-string image.repository=test/model --set-string image.tag=test`
  - result: rendered deployment includes the same runtime baseline with:
    - `/tmp` `emptyDir`
    - `/models` `emptyDir`

- `helm template orchestrator charts/common-service -f charts/values/orchestrator.yaml --set-string image.repository=test/orchestrator --set-string image.tag=test`
  - result: rendered deployment includes the same runtime baseline with `runAsUser: 1000` and `/tmp` `emptyDir`

- `helm template siem-agent charts/common-service -f charts/values/siem-agent.yaml --set-string image.repository=test/siem --set-string image.tag=test`
  - result: rendered deployment includes the same runtime baseline with `runAsUser: 1000` and `/tmp` `emptyDir`

### Source Sweep Evidence

- launch Dockerfiles now resolve to explicit non-root runtime users:
  - `frontend/Dockerfile` -> `USER nextjs:nodejs`
  - `backend/services/api_gateway/Dockerfile` -> `USER sentinelgrid`
  - `backend/services/orchestrator/Dockerfile` -> `USER sentinelgrid`
  - `backend/agents/iam_agent/Dockerfile` -> `USER sentinelgrid`
- `frontend/Dockerfile` now places nginx runtime writes under `/tmp` and the startup command uses `node_modules/.bin/next start`
- the shared chart now renders both `podSecurityContext` and container `securityContext`

### Container Verification Evidence

- Docker daemon connectivity was confirmed, but the local workstation did not already have the required base images cached:
  - `docker image inspect node:20-alpine sentinelgrid/api-base:latest python:3.11-slim sentinelgrid/api-ml:latest`
  - result: first lookup failed on missing `node:20-alpine`, confirming real runtime build verification would require image pulls or local base-image builds
- a real build verification was started for the hardened frontend image:
  - `docker build -t sentinelgrid-slice3c-frontend-test -f frontend/Dockerfile frontend`
  - result in this turn:
    - Dockerfile load, Docker Hub metadata resolution, and base-image pull succeeded
    - the build advanced through `npm ci` and into `npm run build`
    - the build then failed on pre-existing frontend ESLint errors in:
      - `src/app/(dashboard)/dashboard/incidents/[id]/__tests__/page.soc-case.test.tsx`
      - `src/app/(dashboard)/dashboard/requests/[id]/__tests__/page.test.tsx`
      - `src/components/onboarding/__tests__/OnboardingWizard.test.tsx`
    Those failures are outside the Slice 3C changes and match the known pre-existing frontend build blocker already present in the repo.

## Residual Risk After Closeout

- This slice closes the runtime hardening baseline in the repo and Helm release contract, but it does not yet provide full end-to-end startup proof for every launch image under a hardened Kubernetes deployment. The strongest live verification still belongs in the deployment rehearsal and re-audit stages.
- The frontend Docker build still inherits a pre-existing application-lint blocker unrelated to this slice. That prevents a clean end-to-end runtime start proof from the image build path until those test-file ESLint errors are corrected.
- `model-gateway` now uses explicit writable mounts for `/models` and `/tmp`, but those mounts are still `emptyDir`. That preserves the current ephemeral runtime posture rather than introducing persistent model storage.
- The frontend image now supports non-root execution with nginx writes redirected to `/tmp`, but full runtime confidence still depends on a completed image build and cluster rollout under the hardened spec.
- `G-07` remains open until `Slice 3D` closes the secret and default-credential portion of the same gate.

## Exit Decision

`Slice 3C` is closed for the current narrowed launch scope.

The narrowed launch chart path now enforces non-root runtime identity, correct pod and container security contexts, explicit writable mounts, seccomp defaults, and read-only root filesystems for the launch workloads. Phase 3 should continue with `Slice 3D`.
