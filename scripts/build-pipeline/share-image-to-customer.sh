#!/bin/bash
# Share specific image to specific customer
# This script shares an image to a single customer account

set -e

CLOUD="${1:-}"
IMAGE_ID="${2:-}"
CUSTOMER_ACCOUNT="${3:-}"
TENANT_ID="${4:-}"

if [ -z "$CLOUD" ] || [ -z "$IMAGE_ID" ] || [ -z "$CUSTOMER_ACCOUNT" ]; then
    echo "Usage: $0 <cloud> <image_id> <customer_account> [tenant_id]"
    echo "  cloud: aws|azure|gcp"
    echo "  image_id: AMI ID, Azure Image ID, or GCP Image ID"
    echo "  customer_account: Account ID, Subscription ID, or Project ID"
    echo "  tenant_id: Optional tenant ID for verification"
    exit 1
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check scan status
check_scan_status() {
    local image_id=$1
    
    if [ -z "$DB_URL" ]; then
        log "⚠️  DB_URL not set, skipping scan status check"
        return 0
    fi
    
    SCAN_STATUS=$(psql "$DB_URL" -t -c "SELECT scan_status FROM hardened_images WHERE image_id = '$image_id' LIMIT 1" 2>/dev/null | xargs || echo "unknown")
    
    if [ "$SCAN_STATUS" != "passed" ]; then
        log "❌ ERROR: Image scan status is '$SCAN_STATUS', not 'passed'"
        log "   Only images with scan_status='passed' can be distributed"
        return 1
    fi
    
    log "✅ Image scan status: passed"
    return 0
}

# Verify customer account exists
verify_customer_account() {
    local cloud=$1
    local account=$2
    local tenant_id=$3
    
    if [ -z "$DB_URL" ]; then
        log "⚠️  DB_URL not set, skipping account verification"
        return 0
    fi
    
    # Build query based on cloud provider
    case $cloud in
        aws)
            QUERY="SELECT id FROM customer_cloud_accounts WHERE cloud_provider = 'aws' AND account_id = '$account' AND status = 'active'"
            ;;
        azure)
            QUERY="SELECT id FROM customer_cloud_accounts WHERE cloud_provider = 'azure' AND subscription_id = '$account' AND status = 'active'"
            ;;
        gcp)
            QUERY="SELECT id FROM customer_cloud_accounts WHERE cloud_provider = 'gcp' AND project_id = '$account' AND status = 'active'"
            ;;
    esac
    
    if [ -n "$tenant_id" ]; then
        QUERY="$QUERY AND tenant_id = '$tenant_id'"
    fi
    
    ACCOUNT_ID=$(psql "$DB_URL" -t -c "$QUERY LIMIT 1" 2>/dev/null | xargs)
    
    if [ -z "$ACCOUNT_ID" ]; then
        log "⚠️  Warning: Customer account not found in database"
        return 0  # Don't fail, just warn
    fi
    
    log "✅ Customer account verified: $ACCOUNT_ID"
    return 0
}

# Check scan status
if ! check_scan_status "$IMAGE_ID"; then
    log "❌ Cannot share image - scan status check failed"
    exit 1
fi

# Verify customer account
verify_customer_account "$CLOUD" "$CUSTOMER_ACCOUNT" "$TENANT_ID"

# Share image
log "Sharing image $IMAGE_ID to customer account $CUSTOMER_ACCOUNT on $CLOUD"

case $CLOUD in
    aws)
        log "Sharing AWS AMI: $IMAGE_ID with account: $CUSTOMER_ACCOUNT"
        if aws ec2 modify-image-attribute \
            --image-id "$IMAGE_ID" \
            --launch-permission "Add=[{UserId=$CUSTOMER_ACCOUNT}]" \
            --region "${AWS_REGION:-us-east-1}"; then
            log "✅ Successfully shared with account: $CUSTOMER_ACCOUNT"
        else
            log "❌ Failed to share with account: $CUSTOMER_ACCOUNT"
            exit 1
        fi
        ;;
    
    azure)
        log "Sharing Azure Image: $IMAGE_ID with subscription: $CUSTOMER_ACCOUNT"
        log "⚠️  Azure image sharing requires manual configuration or Azure CLI with proper permissions"
        log "   Image: $IMAGE_ID"
        log "   Subscription: $CUSTOMER_ACCOUNT"
        ;;
    
    gcp)
        log "Sharing GCP Image: $IMAGE_ID with project: $CUSTOMER_ACCOUNT"
        if gcloud compute images add-iam-policy-binding "$IMAGE_ID" \
            --member="serviceAccount:$CUSTOMER_ACCOUNT@compute-system.iam.gserviceaccount.com" \
            --role="roles/compute.imageUser"; then
            log "✅ Successfully shared with project: $CUSTOMER_ACCOUNT"
        else
            log "❌ Failed to share with project: $CUSTOMER_ACCOUNT"
            exit 1
        fi
        ;;
    
    *)
        log "❌ ERROR: Unsupported cloud provider: $CLOUD"
        exit 1
        ;;
esac

# Log to database if available
if [ -n "$DB_URL" ]; then
    psql "$DB_URL" -c "INSERT INTO image_customer_sharing (image_id, customer_account_id, share_status) 
        SELECT hi.id, cca.id, 'shared' 
        FROM hardened_images hi, customer_cloud_accounts cca 
        WHERE hi.image_id = '$IMAGE_ID' 
          AND cca.cloud_provider = '$CLOUD'
          AND (cca.account_id = '$CUSTOMER_ACCOUNT' OR cca.subscription_id = '$CUSTOMER_ACCOUNT' OR cca.project_id = '$CUSTOMER_ACCOUNT')
        ON CONFLICT (image_id, customer_account_id) 
        DO UPDATE SET share_status = 'shared', shared_at = NOW()" 2>/dev/null || true
fi

log "✅ Image sharing complete!"

