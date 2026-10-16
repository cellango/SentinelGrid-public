# SentinelGrid GCP Integration - Deployment Manager

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


This directory contains Deployment Manager templates for setting up SentinelGrid GCP integration.

## Prerequisites

- GCP project with Deployment Manager API enabled
- `gcloud` CLI installed and authenticated
- Permissions to create service accounts and assign IAM roles

## Usage

### Step 1: Deploy the Template

```bash
gcloud deployment-manager deployments create sentinelgrid-integration \
  --template=deployment-manager/sentinelgrid-integration.yaml \
  --project=your-project-id
```

### Step 2: Create Service Account Key

After deployment, create a JSON key:

```bash
# Get the service account email from deployment outputs
SERVICE_ACCOUNT_EMAIL=$(gcloud deployment-manager deployments describe sentinelgrid-integration \
  --format="value(outputs.serviceAccountEmail.value)" \
  --project=your-project-id)

# Create the key
gcloud iam service-accounts keys create sentinelgrid-key.json \
  --iam-account=$SERVICE_ACCOUNT_EMAIL \
  --project=your-project-id
```

### Step 3: Collect Values for SentinelGrid UI

You now have all required values:

1. **Project ID**: Your GCP project ID
2. **Service Account Email**: From deployment outputs
3. **Service Account JSON Key**: Contents of `sentinelgrid-key.json`

Paste these into the SentinelGrid onboarding wizard!

## Alternative: Using gcloud CLI Directly

If you prefer not to use Deployment Manager:

```bash
# Set variables
PROJECT_ID="your-project-id"
SERVICE_ACCOUNT_ID="sentinelgrid-monitor"

# Create service account
gcloud iam service-accounts create $SERVICE_ACCOUNT_ID \
  --display-name="SentinelGrid Monitoring" \
  --description="Service account for SentinelGrid monitoring" \
  --project=$PROJECT_ID

SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_ID@$PROJECT_ID.iam.gserviceaccount.com"

# Assign roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/iam.securityReviewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudasset.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/logging.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/monitoring.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/securitycenter.adminViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/compute.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectViewer"

# Create key
gcloud iam service-accounts keys create sentinelgrid-key.json \
  --iam-account=$SERVICE_ACCOUNT_EMAIL \
  --project=$PROJECT_ID

# Output values
echo "Project ID: $PROJECT_ID"
echo "Service Account Email: $SERVICE_ACCOUNT_EMAIL"
echo "Service Account Key: sentinelgrid-key.json"
```

## Cleanup

To remove the deployment:

```bash
gcloud deployment-manager deployments delete sentinelgrid-integration \
  --project=your-project-id
```

## Troubleshooting

### Error: Deployment Manager API not enabled

Enable it:
```bash
gcloud services enable deploymentmanager.googleapis.com
```

### Error: Insufficient permissions

Ensure you have:
- `Service Account Admin` role
- `Service Account Key Admin` role
- `Project IAM Admin` role

### Error: Service account already exists

Delete the existing service account first, or use a different service account ID.

