#!/bin/bash
# Distribute hardened images to specified accounts/subscriptions
# This script shares images across cloud providers
# Enhanced to query database for customer accounts and verify scan status

set -e

CLOUD="${1:-}"
IMAGE_ID="${2:-}"
ACCOUNTS="${3:-}"
TENANT_ID="${4:-}"  # Optional: filter by tenant_id

if [ -z "$CLOUD" ] || [ -z "$IMAGE_ID" ]; then
    echo "Usage: $0 <cloud> <image_id> [accounts] [tenant_id]"
    echo "  cloud: aws|azure|gcp"
    echo "  image_id: AMI ID, Azure Image ID, or GCP Image ID"
    echo "  accounts: Optional comma-separated list of account IDs (if not provided, queries database)"
    echo "  tenant_id: Optional tenant ID to filter customer accounts"
    exit 1
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check scan status before distributing
check_scan_status() {
    local image_id=$1
    
    if [ -z "$DB_URL" ]; then
        log "⚠️  DB_URL not set, skipping scan status check"
        return 0
    fi
    
    # Query database for scan status
    SCAN_STATUS=$(psql "$DB_URL" -t -c "SELECT scan_status FROM hardened_images WHERE image_id = '$image_id' LIMIT 1" 2>/dev/null | xargs || echo "unknown")
    
    if [ "$SCAN_STATUS" != "passed" ]; then
        log "❌ ERROR: Image scan status is '$SCAN_STATUS', not 'passed'"
        log "   Only images with scan_status='passed' can be distributed"
        return 1
    fi
    
    log "✅ Image scan status: passed"
    return 0
}

# Get customer accounts from database
get_customer_accounts() {
    local cloud=$1
    local tenant_id=$2
    
    if [ -z "$DB_URL" ]; then
        log "⚠️  DB_URL not set, cannot query customer accounts"
        return 1
    fi
    
    # Build query
    QUERY="SELECT account_id, subscription_id, project_id FROM customer_cloud_accounts WHERE cloud_provider = '$cloud' AND status = 'active'"
    
    if [ -n "$tenant_id" ]; then
        QUERY="$QUERY AND tenant_id = '$tenant_id'"
    fi
    
    # Execute query and get accounts
    psql "$DB_URL" -t -c "$QUERY" 2>/dev/null | while read -r line; do
        # Extract account ID based on cloud provider
        case $cloud in
            aws)
                echo "$line" | awk '{print $1}'
                ;;
            azure)
                echo "$line" | awk '{print $2}'
                ;;
            gcp)
                echo "$line" | awk '{print $3}'
                ;;
        esac
    done
}

# Check scan status first
if ! check_scan_status "$IMAGE_ID"; then
    log "❌ Cannot distribute image - scan status check failed"
    exit 1
fi

# Get accounts if not provided
if [ -z "$ACCOUNTS" ]; then
    log "No accounts specified, querying database for customer accounts..."
    ACCOUNTS=$(get_customer_accounts "$CLOUD" "$TENANT_ID" | tr '\n' ',' | sed 's/,$//')
    
    if [ -z "$ACCOUNTS" ]; then
        log "No active customer accounts found for cloud provider: $CLOUD"
        exit 0
    fi
    
    log "Found customer accounts: $ACCOUNTS"
fi

case $CLOUD in
    aws)
        log "Sharing AWS AMI: $IMAGE_ID"
        
        SHARED_COUNT=0
        FAILED_COUNT=0
        
        echo "$ACCOUNTS" | tr ',' '\n' | while read account; do
            if [ -z "$account" ]; then
                continue
            fi
            
            log "Sharing with AWS account: $account"
            if aws ec2 modify-image-attribute \
                --image-id "$IMAGE_ID" \
                --launch-permission "Add=[{UserId=$account}]" \
                --region "${AWS_REGION:-us-east-1}" 2>&1; then
                log "✅ Successfully shared with account: $account"
                SHARED_COUNT=$((SHARED_COUNT + 1))
                
                # Log to database if available
                if [ -n "$DB_URL" ]; then
                    psql "$DB_URL" -c "INSERT INTO image_customer_sharing (image_id, customer_account_id, share_status) 
                        SELECT hi.id, cca.id, 'shared' 
                        FROM hardened_images hi, customer_cloud_accounts cca 
                        WHERE hi.image_id = '$IMAGE_ID' AND cca.account_id = '$account' AND cca.cloud_provider = 'aws'
                        ON CONFLICT DO NOTHING" 2>/dev/null || true
                fi
            else
                log "❌ WARNING: Failed to share with account $account"
                FAILED_COUNT=$((FAILED_COUNT + 1))
            fi
        done
        
        log "Shared with $SHARED_COUNT account(s), $FAILED_COUNT failed"
        ;;
    
    azure)
        log "Sharing Azure Image: $IMAGE_ID"
        
        if [ -z "$ACCOUNTS" ]; then
            log "No subscriptions specified, skipping share"
            exit 0
        fi
        
        # Azure image sharing requires different approach
        # Images are typically shared via resource groups or subscriptions
        log "Azure image sharing requires manual configuration via Azure Portal or CLI"
        log "Image: $IMAGE_ID"
        log "Target subscriptions: $ACCOUNTS"
        ;;
    
    gcp)
        log "Sharing GCP Image: $IMAGE_ID"
        
        if [ -z "$ACCOUNTS" ]; then
            log "No projects specified, skipping share"
            exit 0
        fi
        
        echo "$ACCOUNTS" | tr ',' '\n' | while read project; do
            log "Sharing with GCP project: $project"
            gcloud compute images add-iam-policy-binding "$IMAGE_ID" \
                --member="serviceAccount:$project@compute-system.iam.gserviceaccount.com" \
                --role="roles/compute.imageUser" || {
                log "WARNING: Failed to share with project $project"
            }
        done
        ;;
    
    *)
        log "ERROR: Unsupported cloud provider: $CLOUD"
        exit 1
        ;;
esac

log "Image distribution complete!"

