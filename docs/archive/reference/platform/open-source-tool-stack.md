# SentinelGrid Open-Source Tool Stack

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Purpose:** Document the curated set of open-source security tools that power SentinelGrid's "security in a box" approach.

---

## Philosophy

We use **curated open-source tools** rather than building everything from scratch. Each tool is:
- Integrated seamlessly into SentinelGrid
- Presented as a unified experience (not "15 random tools")
- Properly attributed and licensed
- Maintained and updated regularly

---

## Tool Stack by Category

### 1. Endpoint & Host Security

#### ✅ Wazuh (Primary)

**Role:** "SentinelGrid Endpoint Protection"  
**License:** GPL v2  
**What it provides:**
- Host-based Intrusion Detection (HIDS)
- File Integrity Monitoring (FIM)
- Configuration assessment (CIS benchmarks)
- OS-level vulnerability detection
- Log collection (syslog, Windows Events)
- Rootkit/malware detection

**Integration:**
- Multi-tenant Wazuh manager cluster in our infrastructure
- Agents installed on customer endpoints
- Alerts and findings feed into:
  - SIEM (OpenSearch indices)
  - Vulnerability dashboards
  - Posture dashboards
  - SOC playbooks

**Attribution:**
- "SentinelGrid Endpoint Protection, powered by Wazuh"
- License compliance: GPL v2 (modifications must be published if distributed)

**Roadmap:**
- Phase 1: Basic agent deployment
- Phase 2: Custom compliance checks
- Phase 3: Automated remediation (future)

---

### 2. Cloud Security Posture Management (CSPM)

#### ✅ Prowler

**Role:** Cloud misconfiguration scanner  
**License:** Apache 2.0  
**What it provides:**
- AWS/Azure/GCP security best-practice assessments
- Compliance checks (CIS, NIST, PCI-DSS, etc.)
- Misconfiguration detection (public S3, unencrypted volumes, etc.)
- Findings mapped to security frameworks

**Integration:**
- Runs in `posture_agent` service
- Scheduled scans (daily/weekly)
- Findings normalized and stored in `posture_findings` table
- Displayed in "Posture Issues" dashboard
- Mapped to NIST/CIS controls

**Usage:**
```bash
# In posture_agent container
prowler aws \
  --role-arn arn:aws:iam::123456789012:role/SentinelGridMonitorRole \
  --external-id <external-id> \
  --output json \
  --output-file /tmp/prowler-results.json
```

---

#### ✅ CloudQuery

**Role:** Cloud asset inventory and CSPM  
**License:** MPL 2.0  
**What it provides:**
- Multi-cloud resource inventory (EC2, S3, IAM, etc.)
- SQL-based querying of cloud resources
- Asset relationship mapping
- Configuration drift detection

**Integration:**
- Runs in `posture_agent` service
- Syncs cloud resources to our data lake
- Feeds SecGPT with rich context for:
  - Incident analysis
  - Posture reasoning
  - Asset discovery
- Powers "Asset Inventory" views

**Usage:**
```yaml
# cloudquery.yml
kind: source
spec:
  name: aws
  path: cloudquery/aws
  version: "vX.X.X"
  destinations: ["postgresql"]
  spec:
    accounts:
      - id: "123456789012"
        role_arn: "arn:aws:iam::123456789012:role/SentinelGridMonitorRole"
        external_id: "<external-id>"
```

---

### 3. Container & Image Security

#### ✅ Trivy

**Role:** Vulnerability and misconfiguration scanner  
**License:** Apache 2.0  
**What it provides:**
- Container image scanning (CVEs)
- Filesystem scanning
- IaC scanning (Terraform, Kubernetes)
- Secret detection
- SBOM generation

**Integration:**
- Runs in `vulnerability_agent` service
- Scans:
  - Container registries (ECR, GCR, ACR)
  - Filesystems on critical servers
  - IaC repositories (optional)
- Results stored in `vulnerability_findings` table
- Displayed in "Vulnerabilities" tab
- Integrated into playbooks (e.g., "Patch High-Risk Server")

**Usage:**
```bash
# Scan container image
trivy image --format json --output /tmp/trivy.json nginx:latest

# Scan filesystem
trivy fs --format json --output /tmp/trivy.json /path/to/scan
```

---

### 4. Network Security (Phase 2+)

#### ⚙️ Suricata

**Role:** Network IDS/IPS  
**License:** GPL v2  
**What it provides:**
- High-performance network traffic inspection
- IDS/IPS rules engine
- Protocol analysis
- Threat detection (port scans, exploits, C2 traffic)

**Integration:**
- Optional "SentinelGrid Network Sensor" appliance/VM
- For customers with network visibility (SPAN/TAP/PCAP)
- Alerts feed into SIEM as "Network" detections
- Phase 2+ feature (not MVP)

---

### 5. Web Application Security (Phase 2+)

#### ⚙️ OWASP ZAP

**Role:** Dynamic Application Security Testing (DAST)  
**License:** Apache 2.0  
**What it provides:**
- Active web application scanning
- Authentication handling
- Vulnerability discovery (XSS, SQLi, etc.)
- API security testing

**Integration:**
- Optional per-app scanning
- Scheduled scans against customer apps
- Findings in "AppSec" dashboards
- Phase 2+ feature

---

#### ⚙️ Nuclei

**Role:** Template-based vulnerability scanner  
**License:** MIT  
**What it provides:**
- Fast vulnerability scanning
- Template-based detection
- External attack surface scanning
- Web app and infrastructure scanning

**Integration:**
- Optional external perimeter scanning
- Findings in "Attack Surface" dashboards
- Phase 2+ feature

---

### 6. DevSec (Phase 3+)

#### 🔮 Gitleaks / TruffleHog

**Role:** Secrets scanning in Git repositories  
**License:** MIT / Apache 2.0  
**What it provides:**
- Hard-coded secrets detection
- API keys, passwords, tokens
- Git history scanning
- CI/CD integration

**Integration:**
- Optional for dev-heavy customers
- Scans GitHub/GitLab repositories
- Findings in "DevSec" dashboards
- Phase 3+ feature

---

#### 🔮 Semgrep

**Role:** Static Application Security Testing (SAST)  
**License:** LGPL 2.1  
**What it provides:**
- Code pattern detection
- Security rule matching
- Multi-language support
- CI/CD integration

**Integration:**
- Optional SAST scanning
- Findings in "Code Security" dashboards
- Phase 3+ feature

---

## MVP Stack (Phase 1)

**Ship with these tools:**

1. ✅ **Wazuh** → Endpoint Protection
2. ✅ **Prowler** → Cloud CSPM
3. ✅ **CloudQuery** → Cloud Inventory
4. ✅ **Trivy** → Container/Image Scanning

**This gives customers:**
- SIEM (logs from all sources)
- Endpoint security (HIDS, FIM, vulns)
- Cloud posture (misconfigs, compliance)
- Vulnerability management (containers, hosts)

**Result:** Complete security platform in one box.

---

## Phase 2+ Stack

**Add later as optional modules:**

5. ⚙️ **Suricata** → Network IDS/IPS
6. ⚙️ **OWASP ZAP** → Web App Scanning
7. ⚙️ **Nuclei** → Attack Surface Scanning

---

## Phase 3+ Stack

**DevSec and advanced features:**

8. 🔮 **Gitleaks** → Secrets Scanning
9. 🔮 **Semgrep** → SAST
10. 🔮 **osquery** → Advanced Endpoint Queries

---

## Integration Architecture

### Service Mapping

```
┌─────────────────────────────────────────────────────────┐
│  SentinelGrid Services                                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  SIEM Agent          →  OpenSearch (SIEM)               │
│    ├─ CloudTrail logs                                   │
│    ├─ GuardDuty findings                                │
│    ├─ Wazuh alerts                                      │
│    └─ Suricata alerts (Phase 2+)                        │
│                                                          │
│  Posture Agent       →  Posture Findings DB            │
│    ├─ Prowler (CSPM scans)                             │
│    └─ CloudQuery (asset inventory)                     │
│                                                          │
│  Vulnerability Agent  →  Vulnerability Findings DB    │
│    ├─ Trivy (containers/images)                        │
│    └─ Wazuh (host vulns)                               │
│                                                          │
│  Endpoint Agent      →  Wazuh Manager                  │
│    └─ Wazuh agent (on customer endpoints)              │
│                                                          │
│  (Future) AppSec Agent →  AppSec Findings DB           │
│    ├─ OWASP ZAP (DAST)                                 │
│    └─ Nuclei (external scanning)                        │
│                                                          │
│  (Future) DevSec Agent →  DevSec Findings DB           │
│    ├─ Gitleaks (secrets)                               │
│    └─ Semgrep (SAST)                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## License Compliance

### GPL v2 Tools (Wazuh, Suricata)

**Requirements:**
- Proper attribution in documentation
- License file included
- Source code modifications published (if we distribute modified versions)
- Clear indication: "Powered by Wazuh" / "Powered by Suricata"

**Our Approach:**
- Use Wazuh as-is (minimal modifications)
- Run Wazuh manager in our infrastructure (SaaS)
- Agents are customer-installed (they download from Wazuh, not us)
- We ingest data, don't distribute Wazuh

### Apache 2.0 / MIT Tools

**Requirements:**
- Attribution in documentation
- License file included
- No distribution restrictions

**Our Approach:**
- Full integration allowed
- Can rebrand as "SentinelGrid [Feature]"
- Still attribute in docs/credits

---

## Maintenance & Updates

### Update Strategy

1. **Automated Updates:**
   - Monitor tool releases
   - Test in staging
   - Deploy updates monthly/quarterly

2. **Security Patches:**
   - Critical patches deployed within 48 hours
   - Tested in staging first

3. **Version Pinning:**
   - Pin tool versions in Docker images
   - Document version compatibility
   - Test upgrades before deploying

### Tool Lifecycle

- **Active:** Regularly updated, fully supported
- **Maintained:** Updated for security, limited new features
- **Deprecated:** Phased out, migration path provided

---

## Documentation Requirements

### For Each Tool

1. **Attribution:**
   - "SentinelGrid [Feature], powered by [Tool]"
   - Link to tool's website
   - License information

2. **Integration Details:**
   - How it's integrated
   - What data it provides
   - Configuration options

3. **User-Facing Docs:**
   - What the tool does (in plain language)
   - How to use it (if customer-facing)
   - Troubleshooting

---

## Next Steps

1. **Phase 1 Implementation:**
   - Set up Wazuh manager (multi-tenant)
   - Integrate Prowler into posture_agent
   - Integrate CloudQuery into posture_agent
   - Integrate Trivy into vulnerability_agent

2. **Testing:**
   - Test each tool integration
   - Validate data flow to SIEM/dashboards
   - Performance testing

3. **Documentation:**
   - Write integration guides
   - Create attribution pages
   - Update user documentation

---

**This is a living document.** Update as we add new tools or change our stack.

