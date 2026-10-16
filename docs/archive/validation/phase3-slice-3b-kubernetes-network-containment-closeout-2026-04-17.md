# Phase 3 Slice 3B Kubernetes Network Containment Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 17, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the launch-scope east-west containment gap so Kubernetes `NetworkPolicy` is no longer ingress-only, internal services are allowlisted by required dependencies instead of broad namespace trust, and public entry points are modeled separately from internal-only workloads.

## Scope Closed In This Slice

- shared Helm support for separate ingress and egress allowlists
- explicit network-policy distinction between public entry points and internal services
- launch-scope east-west dependency allowlists for `frontend`, `api-gateway`, `iam-agent`, `model-gateway`, `orchestrator`, and `siem-agent`
- removal of the broad `sg-core` ingress trust pattern from the narrowed launch values
- internalization of `model-gateway` ingress so it is no longer rendered as a public release path
- deploy-runbook verification steps for network-policy inspection after rollout

## Code And Config Areas Closed

- `charts/common-service/templates/_helpers.tpl`
- `charts/common-service/templates/networkpolicy.yaml`
- `charts/common-service/values.yaml`
- `charts/values/frontend.yaml`
- `charts/values/api-gateway.yaml`
- `charts/values/iam-agent.yaml`
- `charts/values/model-gateway.yaml`
- `charts/values/orchestrator.yaml`
- `charts/values/siem-agent.yaml`
- `charts/README.md`
- `docs/archive/operations/production-release-and-deploy.md`

## What Changed

1. `charts/common-service/templates/networkpolicy.yaml` now supports a structured ingress and egress contract instead of only ingress allowlists. The chart can now render:
   - public ingress for launch-facing entry points
   - service-instance ingress allowlists for internal services
   - DNS egress
   - specific east-west service egress
   - limited non-service port egress for infrastructure dependencies
2. `charts/common-service/values.yaml` now defines first-class network policy fields for:
   - `networkPolicy.ingress.public`
   - `networkPolicy.ingress.ports`
   - `networkPolicy.ingress.allowNamespaces`
   - `networkPolicy.ingress.allowPodSelectors`
   - `networkPolicy.ingress.allowServiceInstances`
   - `networkPolicy.egress.allowDNS`
   - `networkPolicy.egress.allowAnyPorts`
   - `networkPolicy.egress.allowNamespaces`
   - `networkPolicy.egress.allowPodSelectors`
   - `networkPolicy.egress.allowServiceInstances`
   The older ingress-only fields remain readable for compatibility, but the narrowed launch values now use the structured model.
3. Namespace matching in the shared chart now uses the built-in Kubernetes namespace label `kubernetes.io/metadata.name` instead of assuming a manual `name=<namespace>` label is present.
4. The narrowed launch values no longer rely on broad namespace ingress trust:
   - `frontend`, `api-gateway`, and `iam-agent` are modeled as public entry points with explicit service-port ingress and explicit egress dependencies
   - `model-gateway`, `orchestrator`, and `siem-agent` are modeled as internal services with explicit service-instance ingress allowlists
5. `model-gateway` no longer renders a public ingress resource in the narrowed launch values. That aligns the charted deployment path with `docs/archive/reference/platform/production-operations-topology-2026-04-15.md`, which treats it as an internal east-west dependency rather than a customer-facing edge.
6. `docs/archive/operations/production-release-and-deploy.md` now includes network-policy verification steps so rollout evidence covers:
   - installed network policies
   - the absence of unintended public ingress exposure for internal services
   - the rendered ingress and egress structure of the launch-scope workloads

## Verification Evidence

### Helm Render Evidence

- `helm template frontend charts/common-service -f charts/values/frontend.yaml --set-string image.repository=test/frontend --set-string image.tag=test --set-string 'ingress.hosts[0].host=app.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/frontend-test`
  - result: rendered `NetworkPolicy` includes:
    - `policyTypes: [Ingress, Egress]`
    - public ingress on `3443/TCP`
    - DNS egress
    - explicit east-west egress only to `api-gateway`, `iam-agent`, `connector-service`, and `detection-service`

- `helm template api-gateway charts/common-service -f charts/values/api-gateway.yaml --set-string image.repository=test/api --set-string image.tag=test --set-string 'ingress.hosts[0].host=api.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/api-test`
  - result: rendered `NetworkPolicy` includes:
    - `policyTypes: [Ingress, Egress]`
    - public ingress on `8000/TCP`
    - namespace match using `kubernetes.io/metadata.name: sg-ops`
    - explicit egress only to declared launch dependencies plus `9200/TCP` for OpenSearch

- `helm template iam-agent charts/common-service -f charts/values/iam-agent.yaml --set-string image.repository=test/iam --set-string image.tag=test --set-string 'ingress.hosts[0].host=auth.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/iam-test`
  - result: rendered `NetworkPolicy` includes public ingress plus explicit service and infrastructure egress only

- `helm template model-gateway charts/common-service -f charts/values/model-gateway.yaml --set-string image.repository=test/model --set-string image.tag=test`
  - result: rendered `NetworkPolicy` includes ingress only from `sg-ops`, `api-gateway`, `orchestrator`, `iam-agent`, and `ingestion-service`, plus explicit egress to DNS, infrastructure ports, and `audit-service`

- `helm template orchestrator charts/common-service -f charts/values/orchestrator.yaml --set-string image.repository=test/orchestrator --set-string image.tag=test`
  - result: rendered `NetworkPolicy` includes explicit service-instance ingress and egress allowlists with no public ingress exposure

- `helm template siem-agent charts/common-service -f charts/values/siem-agent.yaml --set-string image.repository=test/siem --set-string image.tag=test`
  - result: rendered `NetworkPolicy` includes explicit service-instance ingress and egress allowlists with no public ingress exposure

### Deny-By-Default Contract Evidence

- `helm template model-gateway charts/common-service -f charts/values/model-gateway.yaml --set-string image.repository=test/model --set-string image.tag=test | rg -n "kind: Ingress|templates/ingress.yaml"`
  - result: no matches, confirming `model-gateway` no longer renders a public ingress resource in the narrowed launch path

- `rg -n "sg-core" charts/values/frontend.yaml charts/values/api-gateway.yaml charts/values/iam-agent.yaml charts/values/model-gateway.yaml charts/values/orchestrator.yaml charts/values/siem-agent.yaml`
  - result: no matches, confirming the previous broad namespace trust pattern is no longer present in the narrowed launch values

- `helm template api-gateway charts/common-service -f charts/values/api-gateway.yaml --set-string image.repository=test/api --set-string image.tag=test --set-string 'ingress.hosts[0].host=api.example.com' --set-string ingress.alb.certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/api-test | rg -n "kubernetes.io/metadata.name|0.0.0.0/0|policyTypes:|egress:"`
  - result: rendered output shows the expected namespace-selector label, public-edge ingress source, explicit `policyTypes`, and explicit `egress` block

### Runbook Evidence

- `docs/archive/operations/production-release-and-deploy.md` now instructs post-deploy verification of:
  - `kubectl get networkpolicy -n <namespace>`
  - `kubectl describe networkpolicy <release> -n <namespace>`
  - absence of unintended public ingress for internal services such as `model-gateway`

## Residual Risk After Closeout

- Public entry points still require `ipBlock: 0.0.0.0/0` on the exposed service port because ALB traffic originates outside the pod network. The actual customer-facing restriction boundary remains the ALB listener, hostname, WAF posture, and application authentication layers.
- Infrastructure egress is now constrained by minimal port allowlists, but not yet by destination identity or CIDR. That is materially better than open east-west traffic, but it is not full identity-based microsegmentation.
- This slice closes the repo and chart contract for network containment, but it does not yet provide live in-cluster packet-deny evidence. That should be captured during the deployment rehearsal and re-audit stages.
- `G-07` remains open until `Slice 3C` and `Slice 3D` close the runtime and secret-hardening portions of the same gate.

## Exit Decision

`Slice 3B` is closed for the current narrowed launch scope.

The narrowed launch chart path now renders explicit ingress and egress containment, internal services are allowlisted by dependency instead of namespace-wide trust, and `model-gateway` is no longer treated as a public ingress surface. Phase 3 should continue with `Slice 3C`.
