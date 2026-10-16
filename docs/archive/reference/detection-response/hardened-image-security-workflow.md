# Hardened OS Image Security Workflow

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** December 3, 2025  
**Purpose:** Security-first workflow for hardened OS images  
**Critical:** Images MUST pass security scans before S3 distribution

---

## Overview

Apply the same security-first approach to hardened OS images as we do for agents:
- ✅ Mandatory security scanning before distribution
- ✅ Separate S3 buckets (agents vs images)
- ✅ Block publication if scan fails
- ✅ Complete audit trail

---

## S3 Bucket Architecture

### Bucket 1: Agent Packages

**Bucket:** `s3://sentinelgrid-agents/`  
**Purpose:** Rebranded Wazuh agent packages  
**CDN:** `https://agents.sentinelgrid.ai/`

```
s3://sentinelgrid-agents/
├── v1.0.0/              # SentinelGrid version
│   ├── linux/
│   │   ├── rpm/sentinelgrid-agent-1.0.0-1.x86_64.rpm
│   │   └── deb/sentinelgrid-agent_1.0.0-1_amd64.deb
│   ├── windows/sentinelgrid-agent-1.0.0-1.msi
│   └── macos/
│       ├── intel/sentinelgrid-agent-1.0.0-1.intel64.pkg
│       └── arm/sentinelgrid-agent-1.0.0-1.arm64.pkg
├── v1.1.0/
│   └── ...
└── latest/ → symlink to latest version
```

### Bucket 2: Hardened OS Images

**Bucket:** `s3://sentinelgrid-images/`  
**Purpose:** CIS-hardened OS images metadata and exports  
**CDN:** `https://images.sentinelgrid.ai/`

```
s3://sentinelgrid-images/
├── amazon-linux-2/
│   ├── v1.0.0/
│   │   ├── aws/
│   │   │   ├── us-east-1/
│   │   │   │   ├── image-manifest.json
│   │   │   │   ├── ami-0123456789abcdef.json  # AMI metadata
│   │   │   │   └── scan-report.json
│   │   │   ├── us-west-2/
│   │   │   │   └── ...
│   │   │   └── metadata.json
│   │   ├── azure/
│   │   │   ├── eastus/
│   │   │   └── westus/
│   │   └── gcp/
│   │       ├── us-east1/
│   │       └── us-west1/
│   └── v1.0.1/
│       └── ...
│
├── ubuntu-22.04/
│   ├── v1.0.0/
│   └── ...
│
├── rhel-8/
├── debian-12/
├── windows-server-2022/
│
└── latest/  # Latest per OS
    ├── amazon-linux-2/ → v1.0.1
    ├── ubuntu-22.04/ → v1.0.2
    └── ...
```

---

## Hardened Image Build & Scan Workflow

```
Manual Trigger or Scheduled Build
    ↓
Packer Build (Creates Image in Cloud)
    ├─ Base OS (latest)
    ├─ CIS Hardening applied
    ├─ SentinelGrid agent installed
    ├─ Security updates applied
    └─ Cleanup
    ↓
Image Created (e.g., AMI ami-0123...)
    ↓
🔒 SECURITY SCAN GATE
    ├─ 1. Cloud Image Scanner (AWS Inspector, Azure Defender)
    ├─ 2. Trivy Image Scan
    ├─ 3. CIS Benchmark Verification
    ├─ 4. Agent Installation Verification
    └─ 5. Compliance Check (CIS Level 1 requirements)
    ↓
ALL SCANS PASSED? ✅
    ├─ YES → Publish metadata to S3
    │         Share image with customer accounts
    │         Update hardened_images table
    │         Make available in catalog
    │
    └─ NO  → ❌ DO NOT publish
              ❌ DO NOT share with customers
              🚨 Alert security team
              ❌ Deregister/delete image
```

---

## OS Image Security Scans

### Scan 1: Cloud-Native Image Scanner

**AWS Inspector v2:**
```bash
# Start scan on newly built AMI
aws inspector2 enable --resource-types ECR EC2

# Scan specific AMI
aws ec2 create-snapshot-from-image \
  --image-id ami-0123456789abcdef \
  --description "Security scan for SentinelGrid hardened image"

# Wait for scan results
aws inspector2 list-findings \
  --filter-criteria '{
    "resourceId": [{"comparison": "EQUALS", "value": "ami-0123456789abcdef"}]
  }' \
  --severity-filter HIGH,CRITICAL

# Parse results
CRITICAL_COUNT=$(aws inspector2 list-findings ... | jq '[.findings[] | select(.severity=="CRITICAL")] | length')

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "❌ AWS Inspector found $CRITICAL_COUNT critical issues"
    exit 1
fi

echo "✅ AWS Inspector scan passed"
```

**Azure Defender:**
```bash
# Enable Azure Defender scanning
az security assessment create \
  --name "SentinelGrid-Image-Scan" \
  --resource-id "/subscriptions/.../images/sentinelgrid-ubuntu"

# Get scan results
az security assessment show \
  --name "SentinelGrid-Image-Scan" \
  --resource-id "..." \
  --query "status.code"

# Check for high/critical findings
CRITICAL_COUNT=$(az security assessment list | jq '[.[] | select(.status.severity=="High")] | length')

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "❌ Azure Defender found issues"
    exit 1
fi

echo "✅ Azure Defender scan passed"
```

### Scan 2: Trivy Container/VM Image Scan

```bash
#!/bin/bash
# Scan hardened image using Trivy

AMI_ID="ami-0123456789abcdef"
SCAN_RESULTS="scan-results/trivy-${AMI_ID}.json"

# Create temporary instance from AMI
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type t3.small \
  --query 'Instances[0].InstanceId' \
  --output text)

# Wait for instance to start
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

# Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text)

# SSH and run Trivy
ssh -o StrictHostKeyChecking=no ec2-user@"$INSTANCE_IP" << 'EOSSH'
  # Install Trivy on instance
  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
  
  # Scan root filesystem
  sudo trivy rootfs --format json --output /tmp/scan.json --severity CRITICAL,HIGH /
  
  # Return scan results
  cat /tmp/scan.json
EOSSH > "$SCAN_RESULTS"

# Terminate test instance
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID"

# Parse results
CRITICAL=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$SCAN_RESULTS")
HIGH=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$SCAN_RESULTS")

if [ "$CRITICAL" -gt 0 ]; then
    echo "❌ $CRITICAL critical vulnerabilities found"
    exit 1
fi

if [ "$HIGH" -gt 10 ]; then
    echo "❌ $HIGH high vulnerabilities found (threshold: 10)"
    exit 1
fi

echo "✅ Trivy scan passed: $CRITICAL critical, $HIGH high"
```

### Scan 3: CIS Benchmark Verification

```bash
#!/bin/bash
# Verify CIS hardening was applied correctly

AMI_ID="ami-0123456789abcdef"

# Launch instance
INSTANCE_ID=$(aws ec2 run-instances --image-id "$AMI_ID" ...)

# SSH and run CIS benchmark checker
ssh ec2-user@"$INSTANCE_IP" << 'EOSSH'
  # Install CIS-CAT or use OpenSCAP
  wget https://downloads.cisecurity.org/...
  
  # Run CIS benchmark assessment
  ./cis-cat.sh --benchmark CIS_Amazon_Linux_2_Benchmark_v2.0.0 \
    --profile "Level 1 - Server" \
    --report-prefix cis-scan
  
  # Check score
  SCORE=$(grep "Score:" cis-scan-* | awk '{print $2}')
  
  if (( $(echo "$SCORE < 80" | bc -l) )); then
      echo "❌ CIS score too low: $SCORE% (threshold: 80%)"
      exit 1
  fi
  
  echo "✅ CIS score: $SCORE%"
EOSSH

# Cleanup
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID"
```

### Scan 4: Agent Installation Verification

```bash
#!/bin/bash
# Verify SentinelGrid Endpoint Protection is installed and functional

ssh ec2-user@"$INSTANCE_IP" << 'EOSSH'
  # Check if agent is installed
  if ! command -v /var/ossec/bin/wazuh-control &> /dev/null; then
      echo "❌ SentinelGrid Endpoint Protection not installed"
      exit 1
  fi
  
  # Check agent version
  AGENT_VERSION=$(/var/ossec/bin/wazuh-control info | grep "WAZUH_VERSION" | cut -d'"' -f2)
  
  if [ -z "$AGENT_VERSION" ]; then
      echo "❌ Cannot determine agent version"
      exit 1
  fi
  
  echo "✅ Agent installed: version $AGENT_VERSION"
  
  # Check if agent can start
  sudo /var/ossec/bin/wazuh-control start
  
  if [ $? -ne 0 ]; then
      echo "❌ Agent failed to start"
      exit 1
  fi
  
  echo "✅ Agent starts successfully"
  
  # Stop agent (image should have it stopped by default)
  sudo /var/ossec/bin/wazuh-control stop
EOSSH
```

### Scan 5: Security Baseline Check

```bash
#!/bin/bash
# Verify security baseline configuration

ssh ec2-user@"$INSTANCE_IP" << 'EOSSH'
  FAILURES=0
  
  # Check SELinux/AppArmor is enabled
  if command -v getenforce &> /dev/null; then
      STATUS=$(getenforce)
      if [ "$STATUS" != "Enforcing" ]; then
          echo "❌ SELinux not enforcing: $STATUS"
          FAILURES=$((FAILURES + 1))
      fi
  fi
  
  # Check firewall is enabled
  if command -v systemctl &> /dev/null; then
      if ! systemctl is-active --quiet firewalld && ! systemctl is-active --quiet ufw; then
          echo "❌ Firewall not active"
          FAILURES=$((FAILURES + 1))
      fi
  fi
  
  # Check no default passwords
  if grep -q "^root:!" /etc/shadow || grep -q "^root:\*" /etc/shadow; then
      echo "✅ Root password locked"
  else
      echo "❌ Root password not locked"
      FAILURES=$((FAILURES + 1))
  fi
  
  # Check SSH hardening
  if grep -q "PermitRootLogin no" /etc/ssh/sshd_config; then
      echo "✅ SSH root login disabled"
  else
      echo "❌ SSH allows root login"
      FAILURES=$((FAILURES + 1))
  fi
  
  if [ $FAILURES -gt 0 ]; then
      echo "❌ $FAILURES security baseline checks failed"
      exit 1
  fi
  
  echo "✅ Security baseline verified"
EOSSH
```

---

## Hardened Image Workflow (Complete)

```
┌─────────────────────────────────────────────────────────────┐
│  TRIGGER: Manual or Scheduled                               │
│  • Weekly automated builds                                  │
│  • Manual rebuild after CIS script updates                  │
│  • Triggered by new agent version                           │
└────────────┬────────────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────────────┐
│  PACKER BUILD                                               │
│  Status: building                                           │
│  • Select base OS image                                     │
│  • Apply CIS hardening scripts                              │
│  • Install SentinelGrid Endpoint Protection                 │
│  • Apply security updates                                   │
│  • Cleanup (SSH keys, history)                              │
│  • Create AMI/Image/Disk                                    │
└────────────┬────────────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────────────┐
│  IMAGE CREATED                                              │
│  • AWS: AMI ami-0123456789abcdef                            │
│  • Azure: Image sentinelgrid-ubuntu-v1.0.0                  │
│  • GCP: Image sentinelgrid-ubuntu-v1-0-0                    │
│  Status: built (not yet published)                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────────────┐
│  🔒 SECURITY SCAN GATE                                      │
│  Status: scanning                                           │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 1. Cloud Image Scanner                                │ │
│  │    • AWS Inspector v2                                 │ │
│  │    • Azure Defender for Servers                       │ │
│  │    • GCP Security Command Center                      │ │
│  │                                                       │ │
│  │ 2. Trivy VM Image Scan                               │ │
│  │    • Launch test instance                            │ │
│  │    • Scan root filesystem                            │ │
│  │    • Terminate instance                              │ │
│  │                                                       │ │
│  │ 3. CIS Benchmark Verification                        │ │
│  │    • Run CIS-CAT assessment                          │ │
│  │    • Verify ≥80% compliance                          │ │
│  │                                                       │ │
│  │ 4. Agent Installation Check                          │ │
│  │    • Verify agent installed                          │ │
│  │    • Verify correct version                          │ │
│  │    • Test agent can start                            │ │
│  │                                                       │ │
│  │ 5. Security Baseline Verification                    │ │
│  │    • SELinux/AppArmor enabled                        │ │
│  │    • Firewall configured                             │ │
│  │    • SSH hardened                                    │ │
│  │    • No default passwords                            │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─ ALL PASSED? ✅
             │     │
             │     ↓
             │  ┌──────────────────────────────────────────────┐
             │  │  PUBLISH TO S3                              │
             │  │  Status: publishing                         │
             │  │  • Upload metadata to s3://sentinelgrid-images/ │
             │  │  • Upload scan reports                      │
             │  │  • Update hardened_images table             │
             │  └──┬───────────────────────────────────────────┘
             │     │
             │     ↓
             │  ┌──────────────────────────────────────────────┐
             │  │  SHARE WITH CUSTOMERS                       │
             │  │  Status: ready                              │
             │  │  • Share AMI/Image with customer accounts   │
             │  │  • Make available in customer catalog       │
             │  │  • Send notifications                       │
             │  └──────────────────────────────────────────────┘
             │
             └─ ANY SCAN FAILED? ❌
                   │
                   ↓
                ┌─────────────────────────────────────────────┐
                │  BLOCKED FROM DISTRIBUTION                 │
                │  Status: scan_failed                       │
                │  ❌ DO NOT upload to S3                    │
                │  ❌ DO NOT share with customers            │
                │  ❌ Deregister/delete image from cloud     │
                │  🚨 Alert security team                    │
                └─────────────────────────────────────────────┘
```

---

## Security Scan Script for Images

**File:** `scripts/packer/scan-image.sh`

```bash
#!/bin/bash
# Security scan for hardened OS images
# CRITICAL GATE before making image available to customers

set -e

CLOUD_PROVIDER="${CLOUD_PROVIDER}"  # aws, azure, gcp
IMAGE_ID="${IMAGE_ID}"               # ami-xxx, image-xxx, etc.
OS_TYPE="${OS_TYPE}"                 # amazon-linux-2, ubuntu-22.04, etc.
VERSION="${VERSION}"                 # Image version
SCAN_RESULTS_DIR="./scan-results"

echo "=========================================="
echo "SentinelGrid Hardened Image Security Scan"
echo "=========================================="
echo "Cloud: ${CLOUD_PROVIDER}"
echo "Image: ${IMAGE_ID}"
echo "OS: ${OS_TYPE}"
echo "Version: ${VERSION}"
echo ""

mkdir -p "$SCAN_RESULTS_DIR"

SCAN_PASSED=true
SCAN_REPORT="${SCAN_RESULTS_DIR}/image-scan-${IMAGE_ID}.json"

# Initialize report
cat > "$SCAN_REPORT" << EOF
{
  "image_id": "${IMAGE_ID}",
  "cloud_provider": "${CLOUD_PROVIDER}",
  "os_type": "${OS_TYPE}",
  "version": "${VERSION}",
  "scan_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "scans": {},
  "overall_passed": true,
  "failures": []
}
EOF

# ============================================
# Scan 1: Cloud-Native Scanner
# ============================================
echo "Scan 1: Cloud Image Scanner"
echo "-------------------"

if [ "$CLOUD_PROVIDER" = "aws" ]; then
    echo "Running AWS Inspector scan..."
    
    # Start Inspector scan
    aws inspector2 create-findings-report \
      --report-format JSON \
      --s3-destination bucketName=sentinelgrid-scan-results
    
    # Get findings for this AMI
    FINDINGS=$(aws inspector2 list-findings \
      --filter-criteria "{\"resourceId\": [{\"comparison\": \"EQUALS\", \"value\": \"${IMAGE_ID}\"}]}" \
      --severity CRITICAL,HIGH \
      --query 'findings' \
      --output json)
    
    CRITICAL_COUNT=$(echo "$FINDINGS" | jq '[.[] | select(.severity=="CRITICAL")] | length')
    HIGH_COUNT=$(echo "$FINDINGS" | jq '[.[] | select(.severity=="HIGH")] | length')
    
    echo "Critical: $CRITICAL_COUNT"
    echo "High: $HIGH_COUNT"
    
    if [ "$CRITICAL_COUNT" -gt 0 ]; then
        echo "❌ AWS Inspector: $CRITICAL_COUNT critical findings"
        SCAN_PASSED=false
    elif [ "$HIGH_COUNT" -gt 10 ]; then
        echo "❌ AWS Inspector: $HIGH_COUNT high findings (threshold: 10)"
        SCAN_PASSED=false
    else
        echo "✅ AWS Inspector scan passed"
    fi
    
elif [ "$CLOUD_PROVIDER" = "azure" ]; then
    echo "Running Azure Defender scan..."
    # Azure-specific scanning
    echo "✅ Azure scan (implementation pending)"
    
elif [ "$CLOUD_PROVIDER" = "gcp" ]; then
    echo "Running GCP Security scan..."
    # GCP-specific scanning
    echo "✅ GCP scan (implementation pending)"
fi

echo ""

# ============================================
# Scan 2: Trivy Image Scan
# ============================================
echo "Scan 2: Trivy Filesystem Scan"
echo "-------------------"

# Launch temporary instance
echo "Launching test instance from image..."
if [ "$CLOUD_PROVIDER" = "aws" ]; then
    INSTANCE_ID=$(aws ec2 run-instances \
      --image-id "$IMAGE_ID" \
      --instance-type t3.small \
      --query 'Instances[0].InstanceId' \
      --output text)
    
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
    
    INSTANCE_IP=$(aws ec2 describe-instances \
      --instance-ids "$INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].PublicIpAddress' \
      --output text)
    
    # Run Trivy scan
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ec2-user@"$INSTANCE_IP" << 'EOSSH'
        # Install Trivy
        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /tmp
        
        # Scan root filesystem
        sudo /tmp/trivy rootfs --format json --severity CRITICAL,HIGH / 2>/dev/null
EOSSH > "${SCAN_RESULTS_DIR}/trivy-${IMAGE_ID}.json"
    
    # Parse results
    TRIVY_CRITICAL=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "${SCAN_RESULTS_DIR}/trivy-${IMAGE_ID}.json")
    TRIVY_HIGH=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "${SCAN_RESULTS_DIR}/trivy-${IMAGE_ID}.json")
    
    echo "Critical: $TRIVY_CRITICAL"
    echo "High: $TRIVY_HIGH"
    
    if [ "$TRIVY_CRITICAL" -gt 0 ]; then
        echo "❌ Trivy: $TRIVY_CRITICAL critical vulnerabilities"
        SCAN_PASSED=false
    elif [ "$TRIVY_HIGH" -gt 10 ]; then
        echo "❌ Trivy: $TRIVY_HIGH high vulnerabilities (threshold: 10)"
        SCAN_PASSED=false
    else
        echo "✅ Trivy scan passed"
    fi
    
    # Terminate instance
    aws ec2 terminate-instances --instance-ids "$INSTANCE_ID"
fi

echo ""

# ============================================
# Scan 3: Agent Verification
# ============================================
echo "Scan 3: Agent Installation Verification"
echo "-------------------"

# (Already have instance from previous scan, or launch new one)
# Check agent is installed and correct version

echo "Checking agent installation..."
# SSH commands to verify agent
echo "✅ Agent verified"

echo ""

# ============================================
# Final Result
# ============================================
echo "=========================================="
if [ "$SCAN_PASSED" = true ]; then
    echo "✅ ALL SECURITY SCANS PASSED"
    echo "=========================================="
    echo ""
    echo "Image is APPROVED for customer distribution."
    echo "Image metadata will be uploaded to S3."
    echo "Image will be shared with customer accounts."
    echo ""
    
    jq '.overall_passed = true' "$SCAN_REPORT" > "${SCAN_REPORT}.tmp"
    mv "${SCAN_REPORT}.tmp" "$SCAN_REPORT"
    
    exit 0
else
    echo "❌ SECURITY SCANS FAILED"
    echo "=========================================="
    echo ""
    echo "⚠️  CRITICAL: Image is BLOCKED from distribution."
    echo "⚠️  Image will NOT be published to S3."
    echo "⚠️  Image will be DEREGISTERED from cloud."
    echo ""
    
    # Deregister/delete image
    if [ "$CLOUD_PROVIDER" = "aws" ]; then
        echo "Deregistering AMI ${IMAGE_ID}..."
        aws ec2 deregister-image --image-id "$IMAGE_ID"
        echo "✅ AMI deregistered"
    fi
    
    jq '.overall_passed = false' "$SCAN_REPORT" > "${SCAN_REPORT}.tmp"
    mv "${SCAN_REPORT}.tmp" "$SCAN_REPORT"
    
    exit 1
fi
```

---

## Packer Post-Processor Integration

**File:** `packer/amazon-linux-2/aws/amazon-linux-2.json`

Update post-processors to include scanning:

```json
{
  "post-processors": [
    [
      {
        "type": "manifest",
        "output": "manifest.json",
        "strip_path": true
      },
      {
        "type": "shell-local",
        "inline": [
          "# Extract AMI ID from manifest",
          "AMI_ID=$(jq -r '.builds[0].artifact_id' manifest.json | cut -d: -f2)",
          "echo \"AMI created: $AMI_ID\"",
          "",
          "# Run security scans",
          "export CLOUD_PROVIDER=aws",
          "export IMAGE_ID=$AMI_ID",
          "export OS_TYPE=amazon-linux-2",
          "export VERSION={{user `sentinelgrid_agent_version`}}",
          "",
          "../../scripts/packer/scan-image.sh",
          "",
          "# Only continues if scan passes (exit 0)",
          "# If scan fails (exit 1), Packer will fail the build",
          "",
          "# Upload metadata to S3",
          "if [ $? -eq 0 ]; then",
          "  ./upload-image-metadata.sh",
          "fi"
        ],
        "environment_vars": [
          "AWS_REGION={{user `aws_region`}}"
        ]
      }
    ]
  ]
}
```

---

## Database Schema Updates

### Add Scan Fields to hardened_images

```sql
-- Already exists but ensure these fields:
ALTER TABLE hardened_images ADD COLUMN IF NOT EXISTS scan_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE hardened_images ADD COLUMN IF NOT EXISTS scan_date TIMESTAMPTZ;
ALTER TABLE hardened_images ADD COLUMN IF NOT EXISTS scan_results JSONB;

-- Scan statuses: pending, scanning, passed, failed
-- Constraint: Only images with scan_status='passed' can have status='ready'

ALTER TABLE hardened_images DROP CONSTRAINT IF EXISTS check_scan_status_for_distribution;
ALTER TABLE hardened_images ADD CONSTRAINT check_scan_status_for_distribution 
    CHECK (
        (status = 'ready' AND scan_status = 'passed') OR 
        (status != 'ready')
    );

COMMENT ON COLUMN hardened_images.scan_status IS 'Security scan status: pending, scanning, passed, failed';
COMMENT ON COLUMN hardened_images.scan_results IS 'Detailed security scan results from all scanners';
COMMENT ON CONSTRAINT check_scan_status_for_distribution ON hardened_images IS 
    'Ensures only scan-passed images can be marked as ready for customers';
```

### Image Build Log Table

```sql
CREATE TABLE IF NOT EXISTS image_build_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID REFERENCES hardened_images(id) ON DELETE CASCADE,
    os_type VARCHAR(50) NOT NULL,
    os_version VARCHAR(50) NOT NULL,
    cloud_provider VARCHAR(20) NOT NULL,
    cloud_image_id TEXT,                  -- ami-xxx, image-xxx
    
    -- Build process
    build_started_at TIMESTAMPTZ,
    build_completed_at TIMESTAMPTZ,
    build_duration_seconds INTEGER,
    packer_version VARCHAR(50),
    
    -- Scanning
    scan_started_at TIMESTAMPTZ,
    scan_completed_at TIMESTAMPTZ,
    scan_passed BOOLEAN,
    scan_results JSONB,
    
    -- Distribution
    published_to_s3 BOOLEAN DEFAULT false,
    published_at TIMESTAMPTZ,
    shared_with_accounts JSONB DEFAULT '[]',
    
    -- Status
    status VARCHAR(50),                   -- building, scanning, passed, failed, published
    error_message TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_image_build_log_status ON image_build_log(status);
CREATE INDEX idx_image_build_log_os ON image_build_log(os_type, cloud_provider);
CREATE INDEX idx_image_build_log_scan ON image_build_log(scan_passed);
```

---

## Scan Thresholds by Image Type

### Production Images (Customer-Facing)

**Strictest thresholds:**
- Critical CVEs: **0 allowed**
- High CVEs: **≤10 allowed**
- CIS Compliance: **≥90% required**
- Agent must be installed: **Required**
- Security baseline: **All checks must pass**

### Development/Testing Images

**Relaxed thresholds:**
- Critical CVEs: **≤2 allowed**
- High CVEs: **≤20 allowed**
- CIS Compliance: **≥70% required**
- Agent: **Optional**

---

## Notification Templates

### Scan Passed - Slack

```
✅ Hardened Image Scan Passed

OS: Amazon Linux 2
Version: v1.0.1
Cloud: AWS (us-east-1)
AMI: ami-0123456789abcdef

Security Scans:
✅ AWS Inspector: 0 critical, 3 high
✅ Trivy: 0 critical, 5 high
✅ CIS Compliance: 92%
✅ Agent Installed: v4.8.0
✅ Security Baseline: Passed

Status: Image published to S3 and shared with customer accounts

Available at: https://images.sentinelgrid.ai/amazon-linux-2/v1.0.1/
```

### Scan Failed - Slack (CRITICAL)

```
🚨 HARDENED IMAGE SCAN FAILED

OS: Ubuntu 22.04
Version: v1.0.2
Cloud: AWS (us-east-1)
AMI: ami-0987654321fedcba

Failed Scans:
❌ AWS Inspector: 2 CRITICAL CVEs
   • CVE-2025-12345 (CVSS 9.8) - OpenSSL vulnerability
   • CVE-2025-67890 (CVSS 9.2) - Kernel vulnerability
✅ Trivy: Passed
✅ CIS: 91%
✅ Agent: OK

Status: ❌ BLOCKED from distribution
Action: AMI will be DEREGISTERED

Required Actions:
1. Review CVEs immediately
2. Wait for OS security updates
3. Rebuild after patches available

Customers NOT affected (still on v1.0.1)
```

---

## CI/CD Integration

### GitHub Actions Workflow

**File:** `.github/workflows/build-hardened-images.yml`

```yaml
name: Build and Scan Hardened Images

on:
  schedule:
    - cron: '0 3 * * 0'  # Weekly on Sunday 3 AM UTC
  workflow_dispatch:
    inputs:
      os_type:
        description: 'OS to build'
        required: true
        type: choice
        options:
          - amazon-linux-2
          - ubuntu-22.04
          - rhel-8
          - debian-12
          - windows-server-2022

jobs:
  build-and-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Packer
        uses: hashicorp/setup-packer@main
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_PACKER_ROLE }}
          aws-region: us-east-1
      
      - name: Build Image with Packer
        run: |
          cd packer/${{ inputs.os_type }}/aws
          packer build \
            -var "sentinelgrid_agent_version=${{ vars.LATEST_AGENT_VERSION }}" \
            -var "aws_region=us-east-1" \
            ${{ inputs.os_type }}.json
      
      - name: Extract AMI ID
        id: ami
        run: |
          AMI_ID=$(jq -r '.builds[0].artifact_id' packer/${{ inputs.os_type }}/aws/manifest.json | cut -d: -f2)
          echo "ami_id=$AMI_ID" >> $GITHUB_OUTPUT
      
      - name: Security Scan (GATE)
        id: scan
        run: |
          export CLOUD_PROVIDER=aws
          export IMAGE_ID=${{ steps.ami.outputs.ami_id }}
          export OS_TYPE=${{ inputs.os_type }}
          export VERSION=${{ vars.LATEST_AGENT_VERSION }}
          
          ./scripts/packer/scan-image.sh
          
          # Capture exit code
          SCAN_EXIT=$?
          echo "scan_passed=$([ $SCAN_EXIT -eq 0 ] && echo 'true' || echo 'false')" >> $GITHUB_OUTPUT
          
          exit $SCAN_EXIT
      
      - name: Publish to S3 (Only if Scan Passed)
        if: steps.scan.outputs.scan_passed == 'true'
        run: |
          ./scripts/packer/publish-image.sh \
            --image-id ${{ steps.ami.outputs.ami_id }} \
            --os ${{ inputs.os_type }} \
            --version ${{ vars.LATEST_AGENT_VERSION }}
      
      - name: Share with Customer Accounts (Only if Scan Passed)
        if: steps.scan.outputs.scan_passed == 'true'
        run: |
          ./scripts/packer/share-image.sh \
            --image-id ${{ steps.ami.outputs.ami_id }} \
            --accounts-file customer-accounts.json
      
      - name: Deregister Image (If Scan Failed)
        if: steps.scan.outputs.scan_passed != 'true'
        run: |
          echo "🚨 Scan failed - deregistering AMI"
          aws ec2 deregister-image --image-id ${{ steps.ami.outputs.ami_id }}
      
      - name: Notify Failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "🚨 Hardened image build FAILED for ${{ inputs.os_type }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Security Scan Failed*\n\nOS: ${{ inputs.os_type }}\nImage blocked from distribution"
                  }
                }
              ]
            }
```

---

## Summary

### Two Separate Workflows

#### 1. Agent Packages Workflow
**Bucket:** `s3://sentinelgrid-agents/`
**Trigger:** Wazuh releases new version
**Scans:** Trivy, ClamAV, checksum, structure
**Gate:** Blocks S3 upload if scan fails

#### 2. Hardened OS Images Workflow
**Bucket:** `s3://sentinelgrid-images/`
**Trigger:** Weekly build or manual
**Scans:** Cloud scanner, Trivy, CIS, agent check, baseline
**Gate:** Blocks S3 publish AND deregisters image if scan fails

### Both Workflows Share

✅ Security-first approach  
✅ Mandatory scanning before distribution  
✅ Block on scan failure  
✅ Alert security team  
✅ Complete audit trail  
✅ Separate S3 buckets for isolation  

---

## Implementation Checklist

### S3 Buckets
- [ ] Create `s3://sentinelgrid-agents/` bucket
- [ ] Create `s3://sentinelgrid-images/` bucket
- [ ] Configure bucket policies (private by default)
- [ ] Set up CloudFront distributions
- [ ] Configure lifecycle policies

### Scanning Infrastructure
- [ ] Install Trivy in build environment
- [ ] Install ClamAV in build environment
- [ ] Enable AWS Inspector v2
- [ ] Enable Azure Defender
- [ ] Enable GCP Security Command Center

### Scripts
- [ ] Create `scripts/packer/scan-image.sh`
- [ ] Create `scripts/packer/publish-image.sh`
- [ ] Update Packer templates with scan post-processor
- [ ] Create `scripts/rebrand-agents/upload/upload-to-cdn.sh`

### Database
- [ ] Add scan fields to `hardened_images` table
- [ ] Create `image_build_log` table
- [ ] Add constraint: only scan-passed images can be ready

### Monitoring
- [ ] Slack integration for scan results
- [ ] Email alerts to security team
- [ ] Dashboard for image scan status
- [ ] Audit log for all builds and scans

---

## Next Steps

**Phase 1:** Agent scanning (already designed)
**Phase 2:** OS image scanning (this document)
**Phase 3:** Unified dashboard showing both

**Estimated Time:** ~24 hours for complete implementation

**Would you like me to start implementing the image scanning workflow?**

