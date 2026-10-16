# SentinelGrid GCP Integration - Main Configuration
# This module creates the necessary Service Account and IAM bindings for SentinelGrid to monitor your GCP project

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Get current project information
data "google_project" "current" {}

# ============================================================================
# Service Account for SentinelGrid Monitoring
# ============================================================================

resource "google_service_account" "sentinelgrid" {
  account_id   = var.service_account_id
  display_name = var.service_account_display_name
  description  = "Service account for SentinelGrid to monitor GCP project (read-only access)"
  project      = data.google_project.current.project_id
}

# ============================================================================
# Service Account Key (JSON Key)
# ============================================================================

resource "google_service_account_key" "sentinelgrid" {
  service_account_id = google_service_account.sentinelgrid.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

# Decode the private key (base64 encoded)
locals {
  service_account_key_json = base64decode(google_service_account_key.sentinelgrid.private_key)
}

# ============================================================================
# IAM Bindings (Read-Only Permissions)
# ============================================================================

# Viewer role - Basic read access to all resources
resource "google_project_iam_member" "viewer" {
  project = data.google_project.current.project_id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.sentinelgrid.email}"
}

# Security Reviewer role - Read security-related resources
resource "google_project_iam_member" "security_reviewer" {
  project = data.google_project.current.project_id
  role    = "roles/iam.securityReviewer"
  member  = "serviceAccount:${google_service_account.sentinelgrid.email}"
}

# Cloud Asset Viewer - Read Cloud Asset Inventory
resource "google_project_iam_member" "cloud_asset_viewer" {
  project = data.google_project.current.project_id
  role    = "roles/cloudasset.viewer"
  member  = "serviceAccount:${google_service_account.sentinelgrid.email}"
}

# Logs Viewer - Read logs from Cloud Logging
resource "google_project_iam_member" "logs_viewer" {
  project = data.google_project.current.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.sentinelgrid.email}"
}

# Monitoring Viewer - Read monitoring data
resource "google_project_iam_member" "monitoring_viewer" {
  project = data.google_project.current.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.sentinelgrid.email}"
}

# Security Center Admin Viewer - Read Security Command Center findings
resource "google_project_iam_member" "security_center_admin_viewer" {
  project = data.google_project.current.project_id
  role    = "roles/securitycenter.adminViewer"
  member  = "serviceAccount:${google_service_account.sentinelgrid.email}"
}

# Cloud SQL Viewer - Read Cloud SQL instance information
resource "google_project_iam_member" "cloud_sql_viewer" {
  project = data.google_project.current.project_id
  role    = "roles/cloudsql.viewer"
  member  = "serviceAccount:${google_service_account.sentinelgrid.email}"
}

# Compute Viewer - Read Compute Engine resources
resource "google_project_iam_member" "compute_viewer" {
  project = data.google_project.current.project_id
  role    = "roles/compute.viewer"
  member  = "serviceAccount:${google_service_account.sentinelgrid.email}"
}

# Storage Object Viewer - Read Cloud Storage objects (for logs)
resource "google_project_iam_member" "storage_object_viewer" {
  project = data.google_project.current.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.sentinelgrid.email}"
}

# ============================================================================
# Optional: Organization-Level Access (if project is in an organization)
# ============================================================================

# Note: Organization-level access requires additional setup and permissions
# This is typically done manually or via separate module

