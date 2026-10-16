#!/bin/bash
# Update package repository metadata
# This script updates APT and YUM repository metadata after adding new packages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Updating Package Repository Metadata"
echo "=========================================="
echo ""

# Function to update APT repository
update_apt_repo() {
    local repo_dir="${SCRIPT_DIR}/../apt-repo"
    
    if [ ! -d "$repo_dir" ]; then
        echo "⚠️  APT repository directory not found: $repo_dir"
        return 1
    fi
    
    echo "📦 Updating APT repository metadata..."
    
    if ! command -v reprepro &> /dev/null; then
        echo "  ⚠️  reprepro not found. Installing..."
        sudo apt-get update -qq
        sudo apt-get install -y reprepro gnupg
    fi
    
    # Update repository
    cd "$repo_dir"
    reprepro export stable || true
    reprepro export testing || true
    
    echo "  ✅ APT repository metadata updated"
}

# Function to update YUM repository
update_yum_repo() {
    local repo_dir="${SCRIPT_DIR}/../yum-repo"
    
    if [ ! -d "$repo_dir" ]; then
        echo "⚠️  YUM repository directory not found: $repo_dir"
        return 1
    fi
    
    echo "📦 Updating YUM repository metadata..."
    
    # Check for createrepo
    CREATEREPO_CMD="createrepo"
    if command -v createrepo_c &> /dev/null; then
        CREATEREPO_CMD="createrepo_c"
    elif ! command -v createrepo &> /dev/null; then
        echo "  ⚠️  createrepo not found. Installing..."
        if command -v yum &> /dev/null; then
            sudo yum install -y createrepo
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y createrepo
        else
            echo "  ❌ Please install createrepo manually"
            return 1
        fi
    fi
    
    # Update metadata for each distribution
    for dist in 7 8 9 2023; do
        if [ -d "$repo_dir/$dist" ]; then
            for arch in x86_64 noarch; do
                if [ -d "$repo_dir/$dist/$arch" ]; then
                    echo "  Updating $dist/$arch..."
                    $CREATEREPO_CMD --update "$repo_dir/$dist/$arch"
                fi
            done
        fi
    done
    
    echo "  ✅ YUM repository metadata updated"
}

# Update repositories
update_apt_repo || true
update_yum_repo || true

echo ""
echo "=========================================="
echo "✅ Metadata update complete!"
echo "=========================================="
echo "Next step: Run deploy-repos-to-cdn.sh to upload to CDN"

