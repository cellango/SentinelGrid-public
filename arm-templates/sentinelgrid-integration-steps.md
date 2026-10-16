# SentinelGrid Azure Integration - ARM Template Deployment Steps

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


Since ARM templates cannot directly create Azure AD applications, follow these steps:

## Step 1: Create Azure AD Application

### Option A: Using Azure Portal

1. Go to **Azure Portal** → **Azure Active Directory** → **App registrations**
2. Click **New registration**
3. Fill in:
   - **Name**: `SentinelGrid Monitoring`
   - **Supported account types**: `Accounts in this organizational directory only`
   - **Redirect URI**: Leave blank (or add `https://api.sentinelgrid.ai/auth/azure/callback` if needed)
4. Click **Register**
5. **Copy these values** (you'll need them):
   - **Application (client) ID**
   - **Directory (tenant) ID**

### Option B: Using Azure CLI

```bash
# Create the application
az ad app create \
  --display-name "SentinelGrid Monitoring" \
  --available-to-other-tenants false

# Get the application ID
APP_ID=$(az ad app list --display-name "SentinelGrid Monitoring" --query "[0].appId" -o tsv)

# Get the tenant ID
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "Application ID: $APP_ID"
echo "Tenant ID: $TENANT_ID"
```

## Step 2: Create Service Principal

### Using Azure CLI

```bash
# Create service principal
az ad sp create --id $APP_ID

# Get the service principal object ID
SP_OBJECT_ID=$(az ad sp show --id $APP_ID --query id -o tsv)

echo "Service Principal Object ID: $SP_OBJECT_ID"
```

## Step 3: Create Client Secret

### Using Azure Portal

1. Go to your application → **Certificates & secrets**
2. Click **New client secret**
3. Fill in:
   - **Description**: `SentinelGrid Monitoring Secret`
   - **Expires**: Choose expiration (recommend 2 years)
4. Click **Add**
5. **Copy the secret value immediately** (you won't see it again!)

### Using Azure CLI

```bash
# Create client secret
az ad app credential reset --id $APP_ID --append

# The output will show the password - copy it!
```

## Step 4: Deploy ARM Template

### Using Azure Portal

1. Go to **Azure Portal** → **Subscriptions** → Your subscription
2. Click **Access control (IAM)**
3. Click **Add** → **Add role assignment**
4. For each role, assign to the Service Principal:
   - **Reader** (acdd72a7-3385-48ef-bd42-f606fba81ae7)
   - **Security Reader** (39bc4728-0917-49c7-9d2c-d95416bc178b)
   - **Log Analytics Reader** (73c42c96-874c-492b-b04d-ab87d138a893)
   - **Monitoring Reader** (43d0d8ad-25c7-4714-9337-8ba259e9fe22)

### Using Azure CLI

```bash
# Assign Reader role
az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "Reader" \
  --scope "/subscriptions/$(az account show --query id -o tsv)"

# Assign Security Reader role
az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "Security Reader" \
  --scope "/subscriptions/$(az account show --query id -o tsv)"

# Assign Log Analytics Reader role
az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "Log Analytics Reader" \
  --scope "/subscriptions/$(az account show --query id -o tsv)"

# Assign Monitoring Reader role
az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "Monitoring Reader" \
  --scope "/subscriptions/$(az account show --query id -o tsv)"
```

## Step 5: Collect Values for SentinelGrid UI

You now have all three required values:

1. **Tenant ID**: From Step 1
2. **Application (Client) ID**: From Step 1
3. **Client Secret**: From Step 3

Paste these into the SentinelGrid onboarding wizard!

## Verification

Test the service principal:

```bash
# Login with service principal
az login --service-principal \
  --username $APP_ID \
  --password "<client-secret>" \
  --tenant $TENANT_ID

# Test reading subscription info
az account show

# Test reading resources (should work with Reader role)
az resource list --query "[].{Name:name, Type:type}" -o table
```

## Troubleshooting

### Error: Insufficient permissions

Ensure you have:
- `Application Administrator` or `Global Administrator` role in Azure AD
- `Owner` or `User Access Administrator` role at subscription level

### Error: Service Principal not found

Make sure you created the service principal in Step 2 before assigning roles.

### Error: Role assignment failed

Check that you're using the Service Principal Object ID (not Application ID) for role assignments.

