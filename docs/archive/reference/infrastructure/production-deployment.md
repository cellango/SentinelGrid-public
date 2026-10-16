# Production Deployment Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This guide covers deploying SentinelGrid to production.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Application Deployment](#application-deployment)
4. [Database Setup](#database-setup)
5. [Keycloak Setup](#keycloak-setup)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)
9. [Security Hardening](#security-hardening)

---

## Prerequisites

### Infrastructure Requirements

**Minimum:**
- 4 CPU cores
- 16 GB RAM
- 100 GB storage
- Kubernetes cluster (or Docker Swarm)

**Recommended:**
- 8+ CPU cores
- 32+ GB RAM
- 500+ GB storage
- Managed Kubernetes (EKS, GKE, AKS)

### Software Requirements

- Kubernetes 1.24+
- Helm 3.0+
- PostgreSQL 15+
- Keycloak 22+
- Nginx Ingress Controller
- Cert-Manager (for SSL)

---

## Infrastructure Setup

### Kubernetes Cluster

**AWS (EKS):**
```bash
eksctl create cluster \
  --name sentinelgrid \
  --region us-east-1 \
  --node-type m5.xlarge \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5
```

**GCP (GKE):**
```bash
gcloud container clusters create sentinelgrid \
  --zone us-central1-a \
  --machine-type n1-standard-4 \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 5
```

**Azure (AKS):**
```bash
az aks create \
  --resource-group sentinelgrid \
  --name sentinelgrid \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaling \
  --min-count 2 \
  --max-count 5
```

---

## Application Deployment

### Using Helm

**Install:**
```bash
helm repo add sentinelgrid https://charts.sentinelgrid.ai
helm install sentinelgrid sentinelgrid/sentinelgrid \
  --namespace sentinelgrid \
  --create-namespace \
  --set database.host=postgres.example.com \
  --set keycloak.url=https://keycloak.example.com \
  --set ingress.host=sentinelgrid.example.com
```

### Using Kubernetes Manifests

**Create namespace:**
```bash
kubectl create namespace sentinelgrid
```

**Deploy secrets:**
```bash
kubectl create secret generic sentinelgrid-secrets \
  --from-literal=db-url=postgresql://... \
  --from-literal=keycloak-admin-password=... \
  --namespace sentinelgrid
```

**Deploy applications:**
```bash
kubectl apply -f k8s/iam-agent.yaml
kubectl apply -f k8s/siem-agent.yaml
kubectl apply -f k8s/api-gateway.yaml
kubectl apply -f k8s/website.yaml
```

---

## Database Setup

### PostgreSQL

**Managed Database (Recommended):**
- AWS RDS
- Google Cloud SQL
- Azure Database for PostgreSQL

**Self-Hosted:**
```bash
# Deploy PostgreSQL
kubectl apply -f k8s/postgresql.yaml

# Run migrations
kubectl exec -it postgres-0 -- \
  psql -U postgres -d sentinelgrid -f /migrations/001_initial.sql
```

**Backup:**
```bash
# Automated backups (daily)
kubectl create cronjob postgres-backup \
  --image=postgres:15 \
  --schedule="0 2 * * *" \
  --restart=OnFailure \
  -- /bin/sh -c "pg_dump -h postgres sentinelgrid > /backups/backup-$(date +%Y%m%d).sql"
```

---

## Keycloak Setup

### Deployment

**Using Helm:**
```bash
helm repo add codecentric https://codecentric.github.io/helm-charts
helm install keycloak codecentric/keycloak \
  --namespace keycloak \
  --create-namespace \
  --set keycloak.username=admin \
  --set keycloak.password=secure-password
```

### Configuration

**Create Realm:**
1. Access Keycloak Admin Console
2. Create new realm: `sentinelgrid`
3. Configure:
   - SSL Required: External
   - User registration: Disabled
   - Email verification: Required

**Create Client:**
1. Clients → Create
2. Client ID: `sentinelgrid-iam-agent`
3. Client Protocol: `openid-connect`
4. Access Type: `confidential`
5. Service Accounts Enabled: `ON`
6. Save and note the Client Secret

---

## SSL/TLS Configuration

### Using Cert-Manager

**Install Cert-Manager:**
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

**Create ClusterIssuer:**
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@sentinelgrid.ai
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

**Ingress with SSL:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sentinelgrid-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - sentinelgrid.example.com
    secretName: sentinelgrid-tls
  rules:
  - host: sentinelgrid.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: website
            port:
              number: 3000
```

---

## Monitoring & Logging

### Prometheus & Grafana

**Install:**
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

**Metrics:**
- API response times
- Request rates
- Error rates
- Database connection pool
- Keycloak health

### Logging

**ELK Stack:**
```bash
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace
helm install kibana elastic/kibana \
  --namespace logging
helm install filebeat elastic/filebeat \
  --namespace logging
```

---

## Backup & Recovery

### Database Backups

**Automated:**
```bash
# CronJob for daily backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command:
            - /bin/sh
            - -c
            - pg_dump -h postgres sentinelgrid | gzip > /backups/backup-$(date +%Y%m%d).sql.gz
            volumeMounts:
            - name: backups
              mountPath: /backups
          volumes:
          - name: backups
            persistentVolumeClaim:
              claimName: postgres-backups
          restartPolicy: OnFailure
```

**Restore:**
```bash
kubectl exec -it postgres-0 -- \
  gunzip -c /backups/backup-20251130.sql.gz | \
  psql -U postgres -d sentinelgrid
```

### Keycloak Backups

**Export Realm:**
```bash
kubectl exec -it keycloak-0 -- \
  /opt/keycloak/bin/kc.sh export \
  --realm sentinelgrid \
  --file /backups/keycloak-export.json
```

---

## Security Hardening

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sentinelgrid-network-policy
spec:
  podSelector:
    matchLabels:
      app: sentinelgrid
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
```

### Pod Security

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: sentinelgrid-app
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

### Secrets Management

**Use External Secrets Operator:**
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

---

## Health Checks

### Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

## Scaling

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sentinelgrid-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sentinelgrid
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Troubleshooting

### Common Issues

**Database Connection:**
```bash
kubectl logs -l app=iam-agent --tail=100
kubectl exec -it postgres-0 -- psql -U postgres -c "SELECT 1"
```

**Keycloak Issues:**
```bash
kubectl logs -l app=keycloak --tail=100
kubectl exec -it keycloak-0 -- /opt/keycloak/bin/kc.sh status
```

**Ingress Issues:**
```bash
kubectl describe ingress sentinelgrid-ingress
kubectl logs -l app.kubernetes.io/name=ingress-nginx --tail=100
```

---

**Last Updated:** 2025-11-30

