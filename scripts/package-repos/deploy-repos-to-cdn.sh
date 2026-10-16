#!/bin/bash
# Deploy package repositories to CDN
# This script uploads APT and YUM repositories to S3/CDN

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDN_BUCKET="${CDN_BUCKET:-agents.sentinelgrid.ai}"
CDN_REGION="${CDN_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-default}"

echo "=========================================="
echo "Deploying Package Repositories to CDN"
echo "=========================================="
echo "Bucket: ${CDN_BUCKET}"
echo ""

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Function to deploy APT repository
deploy_apt_repo() {
    local repo_dir="${SCRIPT_DIR}/../apt-repo"
    
    if [ ! -d "$repo_dir" ]; then
        echo "⚠️  APT repository directory not found: $repo_dir"
        echo "   Run setup-apt-repo.sh first"
        return 1
    fi
    
    echo "📦 Deploying APT repository..."
    
    # Upload dists directory
    if [ -d "$repo_dir/dists" ]; then
        aws s3 sync "$repo_dir/dists" "s3://${CDN_BUCKET}/apt/dists" \
            --region "${CDN_REGION}" \
            --delete \
            --acl public-read
        echo "  ✅ APT dists uploaded"
    fi
    
    # Upload pool directory
    if [ -d "$repo_dir/pool" ]; then
        aws s3 sync "$repo_dir/pool" "s3://${CDN_BUCKET}/apt/pool" \
            --region "${CDN_REGION}" \
            --delete \
            --acl public-read
        echo "  ✅ APT pool uploaded"
    fi
    
    # Upload GPG key
    if [ -f "$repo_dir/gpg.key" ]; then
        aws s3 cp "$repo_dir/gpg.key" "s3://${CDN_BUCKET}/apt/gpg.key" \
            --region "${CDN_REGION}" \
            --acl public-read \
            --content-type "application/pgp-keys"
        echo "  ✅ GPG key uploaded"
    fi
}

# Function to deploy YUM repository
deploy_yum_repo() {
    local repo_dir="${SCRIPT_DIR}/../yum-repo"
    
    if [ ! -d "$repo_dir" ]; then
        echo "⚠️  YUM repository directory not found: $repo_dir"
        echo "   Run setup-yum-repo.sh first"
        return 1
    fi
    
    echo "📦 Deploying YUM repository..."
    
    # Upload repository files
    aws s3 sync "$repo_dir" "s3://${CDN_BUCKET}/yum" \
        --region "${CDN_REGION}" \
        --delete \
        --exclude "*.sh" \
        --exclude "*.md" \
        --exclude "*.txt" \
        --acl public-read
    
    # Upload repository configuration
    if [ -f "$repo_dir/sentinelgrid.repo" ]; then
        aws s3 cp "$repo_dir/sentinelgrid.repo" "s3://${CDN_BUCKET}/yum/sentinelgrid.repo" \
            --region "${CDN_REGION}" \
            --acl public-read \
            --content-type "text/plain"
        echo "  ✅ Repository config uploaded"
    fi
    
    # Upload GPG key
    if [ -f "$repo_dir/RPM-GPG-KEY-sentinelgrid" ]; then
        aws s3 cp "$repo_dir/RPM-GPG-KEY-sentinelgrid" "s3://${CDN_BUCKET}/yum/RPM-GPG-KEY-sentinelgrid" \
            --region "${CDN_REGION}" \
            --acl public-read \
            --content-type "application/pgp-keys"
        echo "  ✅ GPG key uploaded"
    fi
    
    echo "  ✅ YUM repository uploaded"
}

# Deploy repositories
deploy_apt_repo || true
deploy_yum_repo || true

echo ""
echo "=========================================="
echo "✅ Deployment complete!"
echo "=========================================="
echo "APT Repository: https://${CDN_BUCKET}/apt/"
echo "YUM Repository: https://${CDN_BUCKET}/yum/"

