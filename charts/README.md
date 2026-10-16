# Helm Charts (Skeleton)

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


This directory contains a reusable chart for SentinelGrid microservices. It is designed to be parameterized via values files per service (image, ports, autoscaling, KEDA, ingress, Vault annotations, etc.). No commands are executed here—this is scaffolding to support the CI/CD plan.

## Chart: `common-service`
- Deployment + Service with optional ingress
- Optional HPA or KEDA ScaledObject (HTTP/queue/custom metrics)
- Optional NetworkPolicy with separate ingress and egress allowlists
- Supports IRSA annotations, Vault injector annotations, extra env/volumes, and sidecars
- Supports ALB-specific ingress contract fields under `ingress.alb` for listener ports, ACM certificate ARN, backend protocol, TLS redirect, and health checks

### Example install (replace values with service-specific files)
```bash
helm upgrade --install api-gateway charts/common-service \
  -f charts/values/api-gateway.yaml \
  --set image.tag=$IMAGE_TAG
```

Add per-service values files under `charts/values/` to keep configuration organized. Update repositories, ports, and scaling knobs per service.
