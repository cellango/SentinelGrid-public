# Quick Test Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Quick Start Testing

### 1. Run Automated Test Suite

```bash
# Run comprehensive test
./scripts/test-agent-and-image-system.sh
```

This will check:
- ✅ All scripts exist and are executable
- ✅ Database migrations exist
- ✅ Packer templates exist
- ✅ Documentation exists
- ✅ Basic functionality (version bumping, scan parsing)

### 2. Test Agent Rebranding (Quick Test)

```bash
# Set up test environment
cd scripts/rebrand-agents
export WAZUH_VERSION=4.8.0
export SENTINELGRID_VERSION=1.0.0-test

# Test download (requires internet)
./download/download-wazuh.sh

# Verify downloads
ls -lh ../../agents/wazuh/
```

### 3. Test Database Schema

```bash
# Set database URL
export DB_URL="postgresql://user:pass@localhost:5432/sentinelgrid"

# Run migrations
psql $DB_URL -f backend/migrations/020_agent_versions.sql
psql $DB_URL -f backend/migrations/021_hardened_images.sql
psql $DB_URL -f backend/migrations/022_customer_cloud_accounts.sql

# Test insert
psql $DB_URL <<EOF
INSERT INTO agent_versions (version, agent_type, upstream_tool, upstream_version, os_compatibility, package_urls, checksums, status, is_latest)
VALUES ('1.0.0-test', 'endpoint', 'wazuh', '4.8.0', '["amazon-linux-2"]'::jsonb, '{}'::jsonb, '{}'::jsonb, 'stable', true);

SELECT version, agent_type FROM agent_versions WHERE version = '1.0.0-test';
EOF
```

### 4. Test Version Management

```bash
cd scripts/version-management

# Test version bumping
./bump-version.sh agent patch 1.0.0
# Should output: 1.0.1

./bump-version.sh agent minor 1.0.0
# Should output: 1.1.0
```

### 5. Test Scan Result Parsing

```bash
cd scripts/build-pipeline

# Create test scan result
cat > /tmp/test-scan.json <<EOF
{
    "scan_status": "passed",
    "scan_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "scanner": "test",
    "vulnerability_count": {
        "critical": 0,
        "high": 2,
        "medium": 5,
        "low": 10
    }
}
EOF

# Test parsing
./parse-scan-results.sh /tmp/test-scan.json
# Should output: ✅ Scan PASSED
```

### 6. Test Packer Template Validation

```bash
# Install Packer first if needed
# macOS: brew install packer
# Linux: Download from https://www.packer.io/downloads

# Validate template
cd packer/amazon-linux-2/aws
packer validate amazon-linux-2.json
```

## Testing with Real Cloud Provider

### Prerequisites

1. **Install Packer**:
   ```bash
   # macOS
   brew install packer
   
   # Linux
   wget https://releases.hashicorp.com/packer/1.9.4/packer_1.9.4_linux_amd64.zip
   unzip packer_1.9.4_linux_amd64.zip
   sudo mv packer /usr/local/bin/
   ```

2. **Configure Cloud Credentials**:
   ```bash
   # AWS
   aws configure
   
   # Azure
   az login
   
   # GCP
   gcloud auth application-default login
   ```

3. **Set Environment Variables**:
   ```bash
   export DB_URL="postgresql://user:pass@localhost:5432/sentinelgrid"
   export AWS_REGION="us-east-1"
   export CDN_BUCKET="your-bucket-name"
   ```

### Full Build Test (AWS Example)

```bash
# 1. Build image (takes 15-30 minutes)
cd scripts/build-pipeline
./build-image.sh amazon-linux-2 aws 1.0.0

# 2. Get image ID from Packer manifest
IMAGE_ID=$(jq -r '.builds[0].artifact_id' ../../packer/amazon-linux-2/aws/manifest.json | cut -d: -f2)

# 3. Scan image
./scan-image.sh aws $IMAGE_ID amazon-linux-2

# 4. Register image
./register-image.sh aws $IMAGE_ID amazon-linux-2 2023 1.0.0 cis-level1 /tmp/sentinelgrid-scan-${IMAGE_ID}.json

# 5. Verify in database
psql $DB_URL -c "SELECT version, scan_status FROM hardened_images WHERE image_id = '$IMAGE_ID';"
```

## Testing API Endpoints

### Start Services

```bash
# Start IAM Agent (if not running)
cd backend/services/iam_agent
python -m uvicorn app.main:app --port 8005 --reload
```

### Test Endpoints

```bash
# Test agent versions endpoint
curl http://localhost:8005/api/v1/agents/versions | jq

# Test hardened images endpoint
curl http://localhost:8005/api/v1/hardened-images?cloud_provider=aws | jq
```

## Common Issues

### "Packer not found"
```bash
# Install Packer
brew install packer  # macOS
# or download from https://www.packer.io/downloads
```

### "Database connection failed"
```bash
# Check DB_URL is set
echo $DB_URL

# Test connection
psql $DB_URL -c "SELECT 1;"
```

### "Script not executable"
```bash
# Fix permissions
chmod +x scripts/**/*.sh
```

## Next Steps

1. ✅ Run automated test suite
2. ✅ Test individual components
3. ✅ Run database migrations
4. ✅ Test with real cloud provider (optional)
5. ✅ Set up CI/CD for automated builds

For detailed testing instructions, see: `docs/archive/reference/infrastructure/testing-agent-and-images.md`

