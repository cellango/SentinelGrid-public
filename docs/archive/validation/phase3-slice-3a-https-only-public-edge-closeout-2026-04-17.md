# Phase 3 Slice 3A HTTPS-Only Public Edge Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 17, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the public-ingress transport gap so the launch-facing edge no longer depends on a plain-HTTP primary listener, the public ALB releases carry an explicit certificate contract, and backend health checks remain correct after the listener model is hardened.

## Scope Closed In This Slice

- shared Helm ingress support for ALB HTTPS listener, certificate, backend-protocol, redirect, and health-check contract fields
- HTTPS-only public ingress values for `api-gateway`, `frontend`, and `iam-agent`
- explicit ACM certificate requirements in the deploy workflow for all internet-facing launch releases
- runbook documentation for listener model, backend protocol, health check path, and certificate expectations
- Helm render failure when a public ingress is marked certificate-required but no certificate ARN is supplied

## Code And Config Areas Closed

- `charts/common-service/templates/ingress.yaml`
- `charts/common-service/values.yaml`
- `charts/values/api-gateway.yaml`
- `charts/values/frontend.yaml`
- `charts/values/iam-agent.yaml`
- `.github/workflows/build-push-deploy.yml`
- `docs/archive/operations/production-release-and-deploy.md`
- `charts/README.md`

## What Changed

1. `charts/common-service/templates/ingress.yaml` now derives ALB annotations from first-class Helm values instead of relying only on free-form annotation blobs. The chart now supports:
   - HTTPS listener definition
   - ACM certificate ARN injection
   - optional HTTP-to-HTTPS redirect support
   - backend protocol selection
   - health-check path, protocol, and port
2. The shared chart now fails the Helm render when `ingress.alb.requireCertificate=true` and `ingress.alb.certificateArn` is empty. That makes missing public-edge TLS configuration a deploy-time error instead of a hidden runtime gap.
3. `charts/values/api-gateway.yaml` is now HTTPS-only on the public edge:
   - listener `443`
   - backend protocol `HTTP`
   - health check `GET /ready`
4. `charts/values/frontend.yaml` is now HTTPS-only on the public edge with the correct backend transport:
   - listener `443`
   - backend protocol `HTTPS`
   - health check `GET /` over `HTTPS`
   This matches the existing frontend container, which terminates TLS on port `3443`.
5. `charts/values/iam-agent.yaml` now carries the same explicit HTTPS certificate contract for the restricted public auth ingress:
   - listener `443`
   - backend protocol `HTTP`
   - health check `GET /health`
6. `.github/workflows/build-push-deploy.yml` now requires:
   - `FRONTEND_CERTIFICATE_ARN`
   - `API_CERTIFICATE_ARN`
   - `IAM_CERTIFICATE_ARN`
   when `deploy=true`, and injects each value into the corresponding Helm release.
7. `docs/archive/operations/production-release-and-deploy.md` now documents the public-edge contract, the ACM certificate requirement, the backend protocol and health-check expectations, and the fact that HTTP-to-HTTPS redirect is optional transitional behavior rather than the default launch posture.

## Verification Evidence

### Helm Render Evidence

- `helm template api-gateway charts/common-service -f charts/values/api-gateway.yaml --set-string image.repository=test/api --set-string image.tag=test --set-string 'ingress.hosts[0].host=api.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/api-test`
  - result: rendered ingress includes:
    - `alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'`
    - `alb.ingress.kubernetes.io/certificate-arn`
    - `alb.ingress.kubernetes.io/backend-protocol: HTTP`
    - `alb.ingress.kubernetes.io/healthcheck-path: /ready`

- `helm template frontend charts/common-service -f charts/values/frontend.yaml --set-string image.repository=test/frontend --set-string image.tag=test --set-string 'ingress.hosts[0].host=app.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/frontend-test`
  - result: rendered ingress includes:
    - `alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'`
    - `alb.ingress.kubernetes.io/certificate-arn`
    - `alb.ingress.kubernetes.io/backend-protocol: HTTPS`
    - `alb.ingress.kubernetes.io/healthcheck-protocol: HTTPS`
    - `alb.ingress.kubernetes.io/healthcheck-path: /`

- `helm template iam-agent charts/common-service -f charts/values/iam-agent.yaml --set-string image.repository=test/iam --set-string image.tag=test --set-string 'ingress.hosts[0].host=auth.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/iam-test`
  - result: rendered ingress includes:
    - `alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'`
    - `alb.ingress.kubernetes.io/certificate-arn`
    - `alb.ingress.kubernetes.io/backend-protocol: HTTP`
    - `alb.ingress.kubernetes.io/healthcheck-path: /health`

### Fail-Closed Evidence

- `helm template api-gateway charts/common-service -f charts/values/api-gateway.yaml --set-string image.repository=test/api --set-string image.tag=test --set-string 'ingress.hosts[0].host=api.example.com'`
  - result: failed with `ingress.alb.certificateArn is required when ingress.alb.requireCertificate=true`

### Source Sweep Evidence

- public internet-facing values now resolve to `listenPorts: '[{"HTTPS":443}]'` in:
  - `charts/values/api-gateway.yaml`
  - `charts/values/frontend.yaml`
  - `charts/values/iam-agent.yaml`
- the deploy workflow now requires the three public certificate ARN environment variables before cluster rollout

## Residual Risk After Closeout

- This slice closes the public listener and certificate contract gap, but it does not complete `G-07`. Network egress containment, pod/runtime hardening, and broader secret/default cleanup remain open in Phase 3.
- The current launch posture uses HTTPS-only listeners rather than mixed HTTP+HTTPS with redirect. That is the stronger default for this repo state. Redirect support exists in the chart for transitional edges, but it is not exercised in the default launch values.
- This slice does not yet restrict which services are allowed to have public ingress beyond the existing launch-scope conventions. That remains partly a deployment-discipline and topology issue until later hardening work closes.

## Exit Decision

`Slice 3A` is closed for the current narrowed launch scope.

The launch-facing ALB edge now has an explicit HTTPS certificate contract, the rendered public listeners are `443`-based instead of plain-HTTP, and the health-check model is defined per public release. Phase 3 should continue with `Slice 3B`.
