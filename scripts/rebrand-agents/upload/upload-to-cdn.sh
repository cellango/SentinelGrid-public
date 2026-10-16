#!/bin/bash
# Upload rebranded agent packages to CDN
# This script uploads built packages to S3/CDN for distribution

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/../../agents-built"
SENTINELGRID_VERSION="${SENTINELGRID_VERSION:-1.0.0}"

# CDN Configuration (should be in environment variables)
CDN_BUCKET="${CDN_BUCKET:-agents.sentinelgrid.ai}"
CDN_REGION="${CDN_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-default}"

echo "=========================================="
echo "Uploading SentinelGrid Agents to CDN"
echo "=========================================="
echo "Bucket: ${CDN_BUCKET}"
echo "Version: ${SENTINELGRID_VERSION}"
echo ""

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check if bucket exists or create it
if ! aws s3 ls "s3://${CDN_BUCKET}" --region "${CDN_REGION}" &>/dev/null; then
    echo "📦 Creating S3 bucket: ${CDN_BUCKET}..."
    aws s3 mb "s3://${CDN_BUCKET}" --region "${CDN_REGION}"
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "${CDN_BUCKET}" \
        --versioning-configuration Status=Enabled \
        --region "${CDN_REGION}"
    
    # Set public read access for packages
    cat > /tmp/bucket-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::${CDN_BUCKET}/*"
        }
    ]
}
EOF
    aws s3api put-bucket-policy \
        --bucket "${CDN_BUCKET}" \
        --policy file:///tmp/bucket-policy.json \
        --region "${CDN_REGION}"
    
    echo "✅ Bucket created and configured"
fi

# Function to upload file with metadata
upload_file() {
    local file=$1
    local platform=$2
    local filename=$(basename "$file")
    local s3_path="v${SENTINELGRID_VERSION}/${platform}/${filename}"
    
    echo "📤 Uploading: ${filename}..."
    
    # Upload with metadata
    aws s3 cp "$file" "s3://${CDN_BUCKET}/${s3_path}" \
        --region "${CDN_REGION}" \
        --metadata "version=${SENTINELGRID_VERSION},platform=${platform}" \
        --acl public-read \
        --content-type "application/octet-stream"
    
    # Upload checksum if exists
    if [ -f "${file}.sha256" ]; then
        aws s3 cp "${file}.sha256" "s3://${CDN_BUCKET}/${s3_path}.sha256" \
            --region "${CDN_REGION}" \
            --acl public-read \
            --content-type "text/plain"
        echo "  ✅ Checksum uploaded"
    fi
    
    # Generate public URL
    local url="https://${CDN_BUCKET}/${s3_path}"
    echo "  ✅ Uploaded: ${url}"
    
    echo "$url" >> /tmp/uploaded-urls.txt
}

# Upload RPM packages
for rpm_file in "${BUILD_DIR}"/*.rpm; do
    if [ -f "$rpm_file" ]; then
        upload_file "$rpm_file" "linux/rpm"
    fi
done

# Upload DEB packages
for deb_file in "${BUILD_DIR}"/*.deb; do
    if [ -f "$deb_file" ]; then
        upload_file "$deb_file" "linux/deb"
    fi
done

# Upload MSI packages (if available)
for msi_file in "${BUILD_DIR}"/*.msi; do
    if [ -f "$msi_file" ]; then
        upload_file "$msi_file" "windows"
    fi
done

# Upload PKG packages (if available)
for pkg_file in "${BUILD_DIR}"/*.pkg; do
    if [ -f "$pkg_file" ]; then
        upload_file "$pkg_file" "macos"
    fi
done

# Create version manifest
echo ""
echo "Creating version manifest..."
cat > /tmp/version-manifest.json <<EOF
{
    "version": "${SENTINELGRID_VERSION}",
    "upstream_tool": "wazuh",
    "upstream_version": "${WAZUH_VERSION:-4.8.0}",
    "release_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "downloads": {
EOF

# Add download URLs to manifest
if [ -f /tmp/uploaded-urls.txt ]; then
    first=true
    while IFS= read -r url; do
        if [ "$first" = true ]; then
            first=false
        else
            echo "," >> /tmp/version-manifest.json
        fi
        platform=$(echo "$url" | sed -n 's|.*/\([^/]*\)/[^/]*$|\1|p')
        filename=$(basename "$url")
        cat >> /tmp/version-manifest.json <<EOF
        "${platform}": {
            "url": "${url}",
            "filename": "${filename}",
            "checksum_url": "${url}.sha256"
        }
EOF
    done < /tmp/uploaded-urls.txt
fi

cat >> /tmp/version-manifest.json <<EOF
    }
}
EOF

# Upload manifest
aws s3 cp /tmp/version-manifest.json "s3://${CDN_BUCKET}/v${SENTINELGRID_VERSION}/manifest.json" \
    --region "${CDN_REGION}" \
    --acl public-read \
    --content-type "application/json"

echo "✅ Version manifest uploaded"

# Also upload as latest
aws s3 cp /tmp/version-manifest.json "s3://${CDN_BUCKET}/latest/manifest.json" \
    --region "${CDN_REGION}" \
    --acl public-read \
    --content-type "application/json"

echo ""
echo "=========================================="
echo "✅ Upload complete!"
echo "=========================================="
echo "Manifest: https://${CDN_BUCKET}/v${SENTINELGRID_VERSION}/manifest.json"
echo "Latest: https://${CDN_BUCKET}/latest/manifest.json"

