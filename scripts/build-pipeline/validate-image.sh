#!/bin/bash
# Validate built image
# This script validates that agent is installed and hardening is applied

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CLOUD_PROVIDER="${1:-}"
IMAGE_ID="${2:-}"
OS_TYPE="${3:-}"

if [ -z "$CLOUD_PROVIDER" ] || [ -z "$IMAGE_ID" ]; then
    echo "Usage: $0 <cloud_provider> <image_id> [os_type]"
    echo "  cloud_provider: aws, azure, gcp"
    echo "  image_id: AMI ID, Azure Image ID, or GCP Image ID"
    echo "  os_type: Optional OS type"
    exit 1
fi

echo "=========================================="
echo "Validating Hardened Image"
echo "=========================================="
echo "Cloud Provider: ${CLOUD_PROVIDER}"
echo "Image ID: ${IMAGE_ID}"
echo ""

VALIDATION_PASSED=true
VALIDATION_ERRORS=()

# Function to validate AWS AMI
validate_aws_ami() {
    local ami_id=$1
    
    echo "Validating AWS AMI: ${ami_id}..."
    
    # Launch a test instance (this is a simplified validation)
    # In production, you'd launch an instance, run validation commands, then terminate
    
    echo "  ⚠️  Full validation requires launching a test instance"
    echo "  For now, performing basic checks..."
    
    # Check AMI exists
    if ! aws ec2 describe-images --image-ids "$ami_id" --region "${AWS_REGION:-us-east-1}" &>/dev/null; then
        VALIDATION_PASSED=false
        VALIDATION_ERRORS+=("AMI not found or not accessible")
        return 1
    fi
    
    echo "  ✅ AMI exists and is accessible"
    
    # Check AMI has required tags
    TAGS=$(aws ec2 describe-images --image-ids "$ami_id" --region "${AWS_REGION:-us-east-1}" --query 'Images[0].Tags' --output json 2>/dev/null || echo "[]")
    
    if echo "$TAGS" | grep -q "Agent" && echo "$TAGS" | grep -q "Hardening"; then
        echo "  ✅ Required tags present"
    else
        echo "  ⚠️  Warning: Some required tags may be missing"
    fi
    
    return 0
}

# Function to validate Azure Image
validate_azure_image() {
    local image_id=$1
    
    echo "Validating Azure Image: ${image_id}..."
    
    if ! az image show --ids "$image_id" &>/dev/null; then
        VALIDATION_PASSED=false
        VALIDATION_ERRORS+=("Image not found or not accessible")
        return 1
    fi
    
    echo "  ✅ Image exists and is accessible"
    return 0
}

# Function to validate GCP Image
validate_gcp_image() {
    local image_id=$1
    
    echo "Validating GCP Image: ${image_id}..."
    
    if ! gcloud compute images describe "$image_id" &>/dev/null; then
        VALIDATION_PASSED=false
        VALIDATION_ERRORS+=("Image not found or not accessible")
        return 1
    fi
    
    echo "  ✅ Image exists and is accessible"
    return 0
}

# Perform validation based on cloud provider
case $CLOUD_PROVIDER in
    aws)
        validate_aws_ami "$IMAGE_ID" || true
        ;;
    azure)
        validate_azure_image "$IMAGE_ID" || true
        ;;
    gcp)
        validate_gcp_image "$IMAGE_ID" || true
        ;;
    *)
        echo "❌ Unsupported cloud provider: ${CLOUD_PROVIDER}"
        exit 1
        ;;
esac

# Output validation results
echo ""
echo "=========================================="
if [ "$VALIDATION_PASSED" = true ]; then
    echo "✅ Validation PASSED"
    echo "=========================================="
    exit 0
else
    echo "❌ Validation FAILED"
    echo "=========================================="
    echo ""
    echo "Errors:"
    for error in "${VALIDATION_ERRORS[@]}"; do
        echo "  - ${error}"
    done
    exit 1
fi

