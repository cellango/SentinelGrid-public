# Infra Provisioning Checklist (AWS EKS + KEDA + Terraform + Helm)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Purpose: Track what’s done and what’s pending before provisioning production-ready infrastructure.

## Done
- Added Terraform scaffolding for VPC + EKS with IRSA (`infra/eks/main.tf`, `variables.tf`).
- Added helm/kubernetes providers (`infra/eks/data.tf`).
- Added Helm releases for core add-ons (scaffold) in Terraform: ALB Ingress Controller, external-dns, cert-manager, KEDA (`infra/eks/addons.tf`).
- Added managed data-plane scaffold: RDS Postgres (pgvector-capable) and AWS OpenSearch domain (`infra/eks/data-planes.tf`).
- Added initial Helm chart scaffold (`charts/common-service`) and example values for key services.
- Added GitHub Actions skeletons for Terraform plan/apply and build/push/deploy (placeholders).

## To Do (before provisioning)
### Terraform/Infra
- Configure remote state backend (S3 + DynamoDB lock).
- Provide real inputs: `aws_region`, domain filters for external-dns, secure RDS creds, proper instance sizes/counts for RDS/OpenSearch.
- Create IRSA roles/policies for add-ons (ALB controller, external-dns, cert-manager, KEDA, OTel/Fluent Bit) and any AWS-integrating services.
- (Optional) Add tainted/dedicated nodegroups if self-hosting stateful components later.
- Tighten SGs/NACLs: data-plane SGs restricted to EKS node SG; VPC-only access for RDS/OpenSearch.
- Add Route53 zone/records and ACM certs for ingress domains.

### Add-ons/Observability
- Finalize Helm values for ALB controller, external-dns (domain filters), cert-manager (ACM issuer), KEDA, OTel/Fluent Bit. Apply via Terraform Helm provider.
- Create namespaces (`sg-core`, `sg-infra`, `sg-ops`, `sg-vault`, `cert-manager`, `keda`, etc.).

### Data planes
- RDS/Aurora: enable pgvector (init script/parameter group), set backups/snapshots, retention, and monitoring.
- OpenSearch: size/zone awareness, FGAC/IAM auth, VPC access only, snapshot policy.

### Secrets/Security
- Plan Vault deployment in `sg-vault` (StatefulSet + PVC) with init/unseal runbook; define roles/policies for services and CI.
- Wire secrets delivery (Vault Agent Injector or AWS Secrets Manager/CSI); remove any plaintext defaults.
- Enforce NetworkPolicies (default deny + allowlists) and ensure Keycloak/internal services have no public ingress; WAF on public ALB.
- Image scanning/signing (ECR scan, optional Cosign), JWT/mTLS where feasible.

### Helm/App layer
- Replace placeholder image repos/hosts/endpoints in Helm values; set IRSA annotations per service.
- Define KEDA triggers/HPA caps per service; set conservative maxReplicas and min=0 where safe.
- Add Helm releases per service (or umbrella) and wire service endpoints (RDS, OpenSearch, embedding).

### CI/CD
- Set GitHub secrets for OIDC roles (`AWS_TERRAFORM_ROLE_ARN`, `AWS_ECR_DEPLOY_ROLE_ARN`).
- Update build/push/deploy workflow with real service matrix (Dockerfiles) and Helm upgrade commands/values; add smoke tests.
- Add migration job (Flyway) step before app rollout.

### Drift/Backups/Runbooks
- Write Ansible playbooks for drift checks (namespaces, NetworkPolicies, PodSecurity, quotas, add-ons).
- Define backup/restore policies for RDS and OpenSearch; document restore runbooks.

### Validation (pre-prod)
- After `terraform apply`: install add-ons → deploy services via Helm → run end-to-end smoke (health, ingest → OpenSearch, embedding → pgvector, frontend/API).
- Review cost caps (nodegroup sizes, KEDA maxReplicas) and security posture (Keycloak internal-only, WAF, NetworkPolicies) before go-live.
