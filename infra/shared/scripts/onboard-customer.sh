#!/bin/bash
# Customer Onboarding Script
# Usage: ./onboard-customer.sh <customer-name> [keycloak-url] [keycloak-admin-password]

set -e

CUSTOMER_NAME=${1:-""}
KEYCLOAK_URL=${2:-"http://localhost:8081"}
KEYCLOAK_PASSWORD=${3:-"admin"}

if [ -z "$CUSTOMER_NAME" ]; then
  echo "Usage: $0 <customer-name> [keycloak-url] [keycloak-admin-password]"
  echo "Example: $0 agribotsai http://localhost:8081 admin"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CUSTOMER_DIR="$PROJECT_ROOT/infra/customers/$CUSTOMER_NAME"
TERRAFORM_DIR="$CUSTOMER_DIR/keycloak/terraform"

echo "=========================================="
echo "Onboarding Customer: $CUSTOMER_NAME"
echo "=========================================="

# Validate customer configuration exists
if [ ! -d "$TERRAFORM_DIR" ]; then
  echo "❌ Error: Customer configuration not found at $TERRAFORM_DIR"
  echo "   Please create the Terraform configuration first."
  exit 1
fi

# Check if terraform.tfvars exists
TFVARS_FILE="$TERRAFORM_DIR/terraform.tfvars"
if [ ! -f "$TFVARS_FILE" ]; then
  echo "⚠️  Warning: terraform.tfvars not found"
  echo "   Creating from example..."
  if [ -f "$TERRAFORM_DIR/terraform.tfvars.example" ]; then
    cp "$TERRAFORM_DIR/terraform.tfvars.example" "$TFVARS_FILE"
    # Update with provided values
    sed -i.bak "s|keycloak_url.*|keycloak_url = \"$KEYCLOAK_URL\"|" "$TFVARS_FILE"
    sed -i.bak "s|keycloak_password.*|keycloak_password = \"$KEYCLOAK_PASSWORD\"|" "$TFVARS_FILE"
    sed -i.bak "s|customer_name.*|customer_name = \"$CUSTOMER_NAME\"|" "$TFVARS_FILE"
    rm -f "$TFVARS_FILE.bak"
    echo "✅ Created terraform.tfvars"
  else
    echo "❌ Error: terraform.tfvars.example not found"
    exit 1
  fi
fi

# Navigate to Terraform directory
cd "$TERRAFORM_DIR"

# Initialize Terraform
echo ""
echo "📦 Initializing Terraform..."
terraform init

# Validate configuration
echo ""
echo "✅ Validating Terraform configuration..."
if ! terraform validate; then
  echo "❌ Validation failed"
  exit 1
fi

# Show plan
echo ""
echo "📋 Planning Terraform changes..."
terraform plan -out=tfplan

# Ask for confirmation
echo ""
read -p "Apply these changes? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
  echo "Cancelled."
  rm -f tfplan
  exit 0
fi

# Apply configuration
echo ""
echo "🚀 Applying Terraform configuration..."
if terraform apply tfplan; then
  echo ""
  echo "✅ Customer $CUSTOMER_NAME onboarded successfully!"
  echo ""
  echo "📊 Configuration Summary:"
  terraform output
  
  # Clean up plan file
  rm -f tfplan
  
  echo ""
  echo "🔐 Next Steps:"
  echo "1. Note the admin username and initial password"
  echo "2. Login to Keycloak admin console"
  echo "3. Test authentication flow"
  echo "4. Update user passwords (initial passwords are temporary)"
else
  echo ""
  echo "❌ Error applying configuration"
  rm -f tfplan
  exit 1
fi

