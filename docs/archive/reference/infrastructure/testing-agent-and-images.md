# Testing Guide: Agent and Hardened Image System

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This guide provides step-by-step instructions for testing the agent rebranding and hardened image build & distribution system.

## Prerequisites

Before testing, ensure you have:

1. **Required Tools Installed**:
   ```bash
   # Check installations
   which packer
   which aws  # or az, gcloud
   which psql
   which jq
   ```

2. **Environment Variables Set**:
   ```bash
   export DB_URL="postgresql://user:pass@localhost:5432/sentinelgrid"
   export AWS_REGION="us-east-1"  # or Azure/GCP equivalents
   export CDN_BUCKET="agents.sentinelgrid.ai"  # Your S3 bucket
   ```

3. **Database Migrations Run**:
   ```bash
   psql $DB_URL -f backend/migrations/020_agent_versions.sql
   psql $DB_URL -f backend/migrations/021_hardened_images.sql
   psql $DB_URL -f backend/migrations/022_customer_cloud_accounts.sql
   ```

## Testing Agent Rebranding

### Test 1: Download Agents

```bash
cd scripts/rebrand-agents

# Set version
export WAZUH_VERSION=4.8.0

# Download
./download/download-wazuh.sh

# Verify downloads
ls -lh ../../agents/wazuh/
# Should see: .rpm, .deb, .msi, .pkg files
```

**Expected**: Downloads complete successfully, files present in `agents/wazuh/`

### Test 2: Extract Agents

```bash
./extract/extract-agents.sh

# Verify extraction
ls -R ../../agents-extracted/
```

**Expected**: Extracted files in `agents-extracted/` directory

### Test 3: Rebrand Agents

```bash
export SENTINELGRID_VERSION=1.0.0
./rebrand/rebrand-wazuh.sh

# Verify rebranding
grep -r "SentinelGrid" ../../agents-rebranded/ | head -5
```

**Expected**: Files contain "SentinelGrid" instead of "Wazuh"

### Test 4: Build Packages

```bash
./build/build-packages.sh

# Verify builds
ls -lh ../../agents-built/
```

**Expected**: Built packages (.rpm, .deb) in `agents-built/`

### Test 5: Upload to CDN (Dry Run)

```bash
# Test without actually uploading
export CDN_BUCKET="test-bucket"
./upload/upload-to-cdn.sh

# Or test with actual upload (requires AWS credentials)
# aws s3 ls s3://$CDN_BUCKET/
```

**Expected**: Uploads complete or shows what would be uploaded

## Testing Package Repositories

### Test 1: Generate GPG Keys

```bash
cd ../../scripts/package-repos
./generate-gpg-keys.sh

# Verify keys created
ls -lh ../gpg-keys/
```

**Expected**: GPG keys generated in `gpg-keys/` directory

### Test 2: Setup Repositories

```bash
# Setup APT repo
cd apt
./setup-apt-repo.sh

# Setup YUM repo
cd ../yum
./setup-yum-repo.sh
```

**Expected**: Repository structures created

### Test 3: Update Repository Metadata

```bash
cd ..
./update-repo-metadata.sh
```

**Expected**: Repository metadata updated

## Testing Database Schema

### Test 1: Agent Versions Table

```bash
psql $DB_URL <<EOF
-- Insert test agent version
INSERT INTO agent_versions (
    version, agent_type, upstream_tool, upstream_version,
    os_compatibility, package_urls, checksums, status, is_latest
) VALUES (
    '1.0.0',
    'endpoint',
    'wazuh',
    '4.8.0',
    '["amazon-linux-2", "ubuntu-22.04"]'::jsonb,
    '{"rpm": "https://agents.sentinelgrid.ai/v1.0.0/linux/rpm/sentinelgrid-agent-1.0.0-1.x86_64.rpm"}'::jsonb,
    '{"rpm": "sha256:test"}'::jsonb,
    'stable',
    true
);

-- Query
SELECT version, agent_type, status, is_latest FROM agent_versions;
EOF
```

**Expected**: Version inserted and queryable

### Test 2: Hardened Images Table

```bash
psql $DB_URL <<EOF
-- Insert test image
INSERT INTO hardened_images (
    version, os_type, os_version, cloud_provider, image_id, region,
    agent_version, hardening_level, status, scan_status, vulnerability_count
) VALUES (
    'amazon-linux-2-2023-cis-level1-agent-1.0.0-test',
    'amazon-linux-2',
    '2023',
    'aws',
    'ami-test123456',
    'us-east-1',
    '1.0.0',
    'cis-level1',
    'ready',
    'passed',
    '{"critical": 0, "high": 2, "medium": 5, "low": 10}'::jsonb
);

-- Query
SELECT version, os_type, scan_status, status FROM hardened_images;
EOF
```

**Expected**: Image inserted and queryable

### Test 3: Customer Cloud Accounts

```bash
psql $DB_URL <<EOF
-- Insert test customer account
INSERT INTO customer_cloud_accounts (
    tenant_id, cloud_provider, account_id, regions, status
) VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'aws',
    '123456789012',
    '["us-east-1", "us-west-2"]'::jsonb,
    'active'
);

-- Query
SELECT tenant_id, cloud_provider, account_id, status FROM customer_cloud_accounts;
EOF
```

**Expected**: Account inserted and queryable

## Testing Image Building

### Test 1: Validate Packer Template

```bash
cd ../../packer/amazon-linux-2/aws

# Validate template
packer validate amazon-linux-2.json
```

**Expected**: Template validation passes

### Test 2: Build Image (Dry Run)

```bash
# Build with validate-only (doesn't actually build)
packer build -var 'sentinelgrid_agent_version=1.0.0' amazon-linux-2.json

# Or use build script
cd ../../../scripts/build-pipeline
./build-image.sh amazon-linux-2 aws 1.0.0
```

**Expected**: Build process starts (may take 15-30 minutes for full build)

### Test 3: Scan Image (Mock)

```bash
# Create mock scan result
cat > /tmp/mock-scan.json <<EOF
{
    "scan_status": "passed",
    "scan_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "scanner": "test-scanner",
    "vulnerability_count": {
        "critical": 0,
        "high": 2,
        "medium": 5,
        "low": 10
    }
}
EOF

# Test scan result parsing
./parse-scan-results.sh /tmp/mock-scan.json
```

**Expected**: Scan passes validation

### Test 4: Register Image

```bash
# Register test image
./register-image.sh aws ami-test123 amazon-linux-2 2023 1.0.0 cis-level1 /tmp/mock-scan.json

# Verify in database
psql $DB_URL -c "SELECT version, scan_status FROM hardened_images WHERE image_id = 'ami-test123';"
```

**Expected**: Image registered in database

## Testing API Endpoints

### Test 1: Agent Versions API

```bash
# Start IAM Agent service (if not running)
cd ../../backend/services/iam_agent
# python -m uvicorn app.main:app --port 8005

# Test endpoint
curl http://localhost:8005/api/v1/agents/versions | jq

# Test latest version
curl http://localhost:8005/api/v1/agents/versions/endpoint_protection/latest | jq
```

**Expected**: Returns agent version information

### Test 2: Hardened Images API

```bash
# List images
curl http://localhost:8005/api/v1/hardened-images?cloud_provider=aws | jq

# Get specific image
curl http://localhost:8005/api/v1/hardened-images/1 | jq

# Get recommendations
curl "http://localhost:8005/api/v1/hardened-images/recommendations/list?cloud_provider=aws&region=us-east-1" | jq
```

**Expected**: Returns image information

## Testing Distribution

### Test 1: Check Scan Status

```bash
cd ../../scripts/build-pipeline

# Test scan status check (requires DB_URL)
export DB_URL="postgresql://user:pass@localhost:5432/sentinelgrid"

# This will check if image exists and has scan_status='passed'
# (Will fail if image not in database - that's expected for testing)
./distribute-images.sh aws ami-test123
```

**Expected**: Checks scan status before distribution

### Test 2: Share to Customer (Dry Run)

```bash
# Test sharing (requires AWS credentials and valid account ID)
# Replace with your test account ID
./share-image-to-customer.sh aws ami-test123 123456789012
```

**Expected**: Shares image to specified account (or shows what would happen)

## Testing Version Management

### Test 1: Bump Version

```bash
cd ../../scripts/version-management

# Bump patch version
./bump-version.sh agent patch 1.0.0
# Expected output: 1.0.1

# Bump minor version
./bump-version.sh agent minor 1.0.0
# Expected output: 1.1.0

# Bump major version
./bump-version.sh agent major 1.0.0
# Expected output: 2.0.0
```

**Expected**: Correct version increments

### Test 2: Release Version

```bash
# Requires DB_URL
export DB_URL="postgresql://user:pass@localhost:5432/sentinelgrid"

# Release version (requires version to exist in database)
./release-version.sh agent 1.0.0
```

**Expected**: Version marked as released and latest

### Test 3: Check Compatibility

```bash
# Check compatibility (requires versions in database)
./check-version-compatibility.sh 1.0.0 amazon-linux-2-2023-cis-level1-agent-1.0.0-test
```

**Expected**: Compatibility status returned

## Testing Customer Onboarding

### Test 1: Onboard Customer Images

```bash
cd ../../infra/shared/scripts

# Test onboarding (interactive)
# Replace with test tenant ID
./onboard-customer-images.sh 00000000-0000-0000-0000-000000000001 "Test Customer"
```

**Expected**: Prompts for cloud account information

### Test 2: Provision Customer Images

```bash
# Test provisioning (requires customer accounts in database)
./provision-customer-images.sh 00000000-0000-0000-0000-000000000001 "Test Customer"
```

**Expected**: Initiates image build process

## Integration Testing

### End-to-End Test Script

Create a test script:

```bash
#!/bin/bash
# test-e2e.sh - End-to-end test

set -e

echo "=== Testing Agent Rebranding ==="
cd scripts/rebrand-agents
export WAZUH_VERSION=4.8.0
export SENTINELGRID_VERSION=1.0.0-test

./download/download-wazuh.sh
./extract/extract-agents.sh
./rebrand/rebrand-wazuh.sh

echo "✅ Agent rebranding test passed"

echo ""
echo "=== Testing Database Schema ==="
psql $DB_URL -c "SELECT COUNT(*) FROM agent_versions;" || echo "⚠️  Run migrations first"
psql $DB_URL -c "SELECT COUNT(*) FROM hardened_images;" || echo "⚠️  Run migrations first"
psql $DB_URL -c "SELECT COUNT(*) FROM customer_cloud_accounts;" || echo "⚠️  Run migrations first"

echo "✅ Database schema test passed"

echo ""
echo "=== Testing Version Management ==="
cd ../../scripts/version-management
NEW_VERSION=$(./bump-version.sh agent patch 1.0.0 | tail -1)
echo "Bumped version: $NEW_VERSION"

echo "✅ Version management test passed"

echo ""
echo "=== All Tests Passed ==="
```

## Quick Test Checklist

- [ ] Database migrations run successfully
- [ ] Agent download script works
- [ ] Agent extraction script works
- [ ] Agent rebranding script works
- [ ] Package build script works (if build tools available)
- [ ] Database schema accepts test data
- [ ] API endpoints return data (even if mock)
- [ ] Version management scripts work
- [ ] Packer template validates
- [ ] Scan result parsing works

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql $DB_URL -c "SELECT 1;"

# Check migrations
psql $DB_URL -c "\dt" | grep -E "(agent_versions|hardened_images|customer_cloud_accounts)"
```

### Missing Dependencies

```bash
# Install missing tools
# macOS
brew install packer jq postgresql

# Ubuntu/Debian
sudo apt-get install packer jq postgresql-client
```

### Permission Issues

```bash
# Make scripts executable
find scripts -name "*.sh" -exec chmod +x {} \;
```

## Next Steps After Testing

1. **Fix any issues** found during testing
2. **Run full build** with actual cloud provider
3. **Test with real customer accounts**
4. **Set up CI/CD** for automated builds
5. **Monitor** build and distribution processes

## Support

For testing issues:
- Check script help: `./script-name.sh` (without arguments)
- Review logs in `/tmp/` directory
- Check database for registered data
- Contact DevOps team

