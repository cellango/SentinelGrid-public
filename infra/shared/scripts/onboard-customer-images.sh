#!/bin/bash
# Collect customer cloud account information during onboarding
# This script prompts for and stores customer cloud account details

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TENANT_ID="${1:-}"
TENANT_NAME="${2:-}"

if [ -z "$TENANT_ID" ] || [ -z "$TENANT_NAME" ]; then
    echo "Usage: $0 <tenant_id> <tenant_name>"
    echo "  tenant_id: UUID of the tenant"
    echo "  tenant_name: Name of the tenant"
    exit 1
fi

echo "=========================================="
echo "Customer Cloud Account Onboarding"
echo "=========================================="
echo "Tenant: ${TENANT_NAME} (${TENANT_ID})"
echo ""

# Function to collect AWS account
collect_aws_account() {
    echo "AWS Account Information:"
    read -p "  AWS Account ID (12 digits): " AWS_ACCOUNT_ID
    read -p "  Regions (comma-separated, e.g., us-east-1,us-west-2): " AWS_REGIONS
    
    if [ -n "$AWS_ACCOUNT_ID" ]; then
        echo "  ✅ AWS account will be registered: ${AWS_ACCOUNT_ID}"
        echo "     Regions: ${AWS_REGIONS:-us-east-1}"
    fi
}

# Function to collect Azure subscription
collect_azure_subscription() {
    echo "Azure Subscription Information:"
    read -p "  Azure Subscription ID: " AZURE_SUBSCRIPTION_ID
    read -p "  Regions (comma-separated, e.g., East US,West US): " AZURE_REGIONS
    
    if [ -n "$AZURE_SUBSCRIPTION_ID" ]; then
        echo "  ✅ Azure subscription will be registered: ${AZURE_SUBSCRIPTION_ID}"
        echo "     Regions: ${AZURE_REGIONS:-East US}"
    fi
}

# Function to collect GCP project
collect_gcp_project() {
    echo "GCP Project Information:"
    read -p "  GCP Project ID: " GCP_PROJECT_ID
    read -p "  Regions (comma-separated, e.g., us-east1,us-west1): " GCP_REGIONS
    
    if [ -n "$GCP_PROJECT_ID" ]; then
        echo "  ✅ GCP project will be registered: ${GCP_PROJECT_ID}"
        echo "     Regions: ${GCP_REGIONS:-us-east1}"
    fi
}

# Collect cloud account information
echo "Please provide cloud account information for image sharing."
echo "You can skip any cloud provider you don't use."
echo ""

read -p "Do you use AWS? (y/N): " USE_AWS
if [[ $USE_AWS =~ ^[Yy]$ ]]; then
    collect_aws_account
fi

read -p "Do you use Azure? (y/N): " USE_AZURE
if [[ $USE_AZURE =~ ^[Yy]$ ]]; then
    collect_azure_subscription
fi

read -p "Do you use GCP? (y/N): " USE_GCP
if [[ $USE_GCP =~ ^[Yy]$ ]]; then
    collect_gcp_project
fi

# Version policy
echo ""
echo "Version Policy:"
echo "  latest - Always use latest version (recommended)"
echo "  stable - Use latest stable version (skip beta)"
echo "  pinned - Pin to specific version"
read -p "Version policy (latest/stable/pinned) [latest]: " VERSION_POLICY
VERSION_POLICY="${VERSION_POLICY:-latest}"

PINNED_VERSION=""
if [ "$VERSION_POLICY" = "pinned" ]; then
    read -p "Pinned version: " PINNED_VERSION
fi

# Register in database
if [ -z "$DB_URL" ]; then
    echo ""
    echo "⚠️  DB_URL not set, cannot register in database"
    echo "   Please run the following SQL manually:"
    echo ""
    
    if [ -n "$AWS_ACCOUNT_ID" ]; then
        cat <<EOF
INSERT INTO customer_cloud_accounts (tenant_id, cloud_provider, account_id, regions, version_policy, pinned_version, status)
VALUES ('${TENANT_ID}', 'aws', '${AWS_ACCOUNT_ID}', '${AWS_REGIONS:-us-east-1}'::jsonb, '${VERSION_POLICY}', ${PINNED_VERSION:+"'${PINNED_VERSION}'"} ${PINNED_VERSION:-NULL}, 'active');
EOF
    fi
    
    if [ -n "$AZURE_SUBSCRIPTION_ID" ]; then
        cat <<EOF
INSERT INTO customer_cloud_accounts (tenant_id, cloud_provider, subscription_id, regions, version_policy, pinned_version, status)
VALUES ('${TENANT_ID}', 'azure', '${AZURE_SUBSCRIPTION_ID}', '${AZURE_REGIONS:-East US}'::jsonb, '${VERSION_POLICY}', ${PINNED_VERSION:+"'${PINNED_VERSION}'"} ${PINNED_VERSION:-NULL}, 'active');
EOF
    fi
    
    if [ -n "$GCP_PROJECT_ID" ]; then
        cat <<EOF
INSERT INTO customer_cloud_accounts (tenant_id, cloud_provider, project_id, regions, version_policy, pinned_version, status)
VALUES ('${TENANT_ID}', 'gcp', '${GCP_PROJECT_ID}', '${GCP_REGIONS:-us-east1}'::jsonb, '${VERSION_POLICY}', ${PINNED_VERSION:+"'${PINNED_VERSION}'"} ${PINNED_VERSION:-NULL}, 'active');
EOF
    fi
else
    # Register via SQL
    if [ -n "$AWS_ACCOUNT_ID" ]; then
        psql "$DB_URL" -c "INSERT INTO customer_cloud_accounts (tenant_id, cloud_provider, account_id, regions, version_policy, pinned_version, status)
            VALUES ('${TENANT_ID}', 'aws', '${AWS_ACCOUNT_ID}', '${AWS_REGIONS:-us-east-1}'::jsonb, '${VERSION_POLICY}', ${PINNED_VERSION:+"'${PINNED_VERSION}'"} ${PINNED_VERSION:-NULL}, 'active')
            ON CONFLICT DO NOTHING" 2>/dev/null && echo "✅ AWS account registered" || echo "⚠️  Failed to register AWS account"
    fi
    
    if [ -n "$AZURE_SUBSCRIPTION_ID" ]; then
        psql "$DB_URL" -c "INSERT INTO customer_cloud_accounts (tenant_id, cloud_provider, subscription_id, regions, version_policy, pinned_version, status)
            VALUES ('${TENANT_ID}', 'azure', '${AZURE_SUBSCRIPTION_ID}', '${AZURE_REGIONS:-East US}'::jsonb, '${VERSION_POLICY}', ${PINNED_VERSION:+"'${PINNED_VERSION}'"} ${PINNED_VERSION:-NULL}, 'active')
            ON CONFLICT DO NOTHING" 2>/dev/null && echo "✅ Azure subscription registered" || echo "⚠️  Failed to register Azure subscription"
    fi
    
    if [ -n "$GCP_PROJECT_ID" ]; then
        psql "$DB_URL" -c "INSERT INTO customer_cloud_accounts (tenant_id, cloud_provider, project_id, regions, version_policy, pinned_version, status)
            VALUES ('${TENANT_ID}', 'gcp', '${GCP_PROJECT_ID}', '${GCP_REGIONS:-us-east1}'::jsonb, '${VERSION_POLICY}', ${PINNED_VERSION:+"'${PINNED_VERSION}'"} ${PINNED_VERSION:-NULL}, 'active')
            ON CONFLICT DO NOTHING" 2>/dev/null && echo "✅ GCP project registered" || echo "⚠️  Failed to register GCP project"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Customer cloud account onboarding complete!"
echo "=========================================="
echo ""
echo "Next step: Run provision-customer-images.sh to build and share initial images"

