# Image Security Scanning Process

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document describes the security scanning process for hardened images.

## Overview

All hardened images are security scanned before distribution to ensure they meet security standards. Only images that pass scanning are made available to customers.

## Scanning Tools

### AWS

- **AWS Inspector v2**: Automated vulnerability scanning
- **EC2 Image Builder**: Integrated scanning pipeline
- **Custom Tools**: Trivy, Clair, or similar

### Azure

- **Azure Security Center**: Vulnerability assessment
- **Defender for Cloud**: Security scanning
- **Container Analysis API**: For container images

### GCP

- **Container Analysis API**: Vulnerability scanning
- **Cloud Security Command Center**: Security posture management
- **Binary Authorization**: Policy enforcement

## Security Policy

### Vulnerability Thresholds

Images must meet these thresholds to pass scanning:

| Severity | Maximum Allowed |
|----------|----------------|
| Critical | 0 |
| High | 5 |
| Medium | 20 |
| Low | 50 |

### Scan Status

- **pending**: Scan not yet performed
- **passed**: Scan passed all checks
- **failed**: Scan failed (vulnerabilities exceed thresholds)

## Scanning Process

### 1. Automated Scanning

After image build, scanning is automatically triggered:

```bash
./scripts/build-pipeline/scan-image.sh aws ami-xxxxxxxxxxxxx amazon-linux-2
```

### 2. Parse Results

Scan results are parsed and validated:

```bash
./scripts/build-pipeline/parse-scan-results.sh /tmp/sentinelgrid-scan-ami-xxxxxxxxxxxxx.json
```

### 3. Database Registration

Scan results are stored in database:

```sql
UPDATE hardened_images
SET scan_status = 'passed',
    scan_date = NOW(),
    scan_results = '...'::jsonb,
    vulnerability_count = '{"critical": 0, "high": 2, "medium": 5, "low": 10}'::jsonb
WHERE image_id = 'ami-xxxxxxxxxxxxx';
```

## Scan Results Format

```json
{
    "scan_status": "passed",
    "scan_date": "2024-11-30T12:00:00Z",
    "scanner": "aws-inspector-v2",
    "vulnerability_count": {
        "critical": 0,
        "high": 2,
        "medium": 5,
        "low": 10
    },
    "vulnerabilities": [
        {
            "id": "CVE-2024-12345",
            "severity": "high",
            "package": "openssl",
            "version": "1.1.1",
            "fixed_version": "1.1.2"
        }
    ],
    "compliance": {
        "cis_level1": "passed",
        "cis_level2": "partial"
    }
}
```

## Distribution Rules

### Only Clean Images Distributed

Images with `scan_status != 'passed'` cannot be distributed:

```sql
-- Constraint enforced in database
ALTER TABLE hardened_images 
ADD CONSTRAINT check_scan_status_for_distribution 
CHECK (
    (status = 'ready' AND scan_status = 'passed') OR 
    (status != 'ready')
);
```

### Distribution Script Check

The distribution script verifies scan status:

```bash
# In distribute-images.sh
check_scan_status() {
    SCAN_STATUS=$(psql "$DB_URL" -t -c "SELECT scan_status FROM hardened_images WHERE image_id = '$image_id'")
    
    if [ "$SCAN_STATUS" != "passed" ]; then
        log "❌ ERROR: Image scan status is '$SCAN_STATUS', not 'passed'"
        return 1
    fi
}
```

## Remediation

### Failed Scans

If an image fails scanning:

1. **Review Vulnerabilities**: Check scan results for details
2. **Update Base Image**: Use newer base image with fixes
3. **Apply Patches**: Update packages in Packer template
4. **Rebuild**: Rebuild image with fixes
5. **Rescan**: Run scan again

### Example Remediation

```bash
# 1. Review scan results
cat /tmp/sentinelgrid-scan-ami-xxxxxxxxxxxxx.json | jq '.vulnerabilities'

# 2. Update Packer template to patch vulnerabilities
# Add to provisioners:
{
    "type": "shell",
    "inline": [
        "sudo yum update -y openssl",
        "sudo yum update -y kernel"
    ]
}

# 3. Rebuild
./build-image.sh amazon-linux-2 aws 1.0.0

# 4. Rescan
./scan-image.sh aws ami-yyyyyyyyyyyyyy amazon-linux-2
```

## Continuous Scanning

### Scheduled Scans

Images can be rescanned periodically:

```bash
# Rescan all active images
psql "$DB_URL" -t -c "SELECT image_id FROM hardened_images WHERE status = 'ready'" | \
while read image_id; do
    ./scan-image.sh aws "$image_id"
done
```

### Automated Rescanning

Set up automated rescanning via CI/CD:

```yaml
# .github/workflows/rescan-images.yml
name: Rescan Images

on:
  schedule:
    - cron: '0 3 * * 0'  # Weekly

jobs:
  rescan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Rescan Images
        run: ./scripts/build-pipeline/rescan-all-images.sh
```

## Reporting

### Scan Reports

Scan results are available via API:

```bash
# Get scan results for image
curl https://api.sentinelgrid.ai/api/v1/hardened-images/{image_id}/scan-results
```

### Dashboard

Scan status is visible in the dashboard:
- Green: Scan passed
- Yellow: Scan pending
- Red: Scan failed

## Best Practices

1. **Scan Early**: Scan images immediately after build
2. **Automate**: Use CI/CD for automated scanning
3. **Monitor**: Track scan status in dashboard
4. **Remediate**: Fix vulnerabilities promptly
5. **Document**: Document any exceptions or waivers

## Support

For issues or questions, contact the DevOps team.

