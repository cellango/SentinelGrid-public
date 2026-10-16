-- Migration 004: Assets Mobile Device Support and Enhancements
-- Date: 2025-01-28
-- Description: Add support for mobile devices and improve asset-user relationships

-- Update asset_type comment to include mobile devices
COMMENT ON COLUMN assets.asset_type IS 'Asset type: server, workstation, network_device, cloud_instance, mobile';

-- Add user_id field to link assets to Keycloak users (optional, owner remains for flexibility)
-- This allows linking to user_tenants table if needed
ALTER TABLE assets ADD COLUMN IF NOT EXISTS user_id TEXT;
COMMENT ON COLUMN assets.user_id IS 'Keycloak user ID (optional, for linking to user_tenants table)';

-- Add index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_assets_user_id ON assets(user_id);

-- Add index for owner lookups (email-based)
CREATE INDEX IF NOT EXISTS idx_assets_owner ON assets(owner);

-- Update comment for owner field to clarify it can be email or user identifier
COMMENT ON COLUMN assets.owner IS 'User/team owner (email or user identifier). Use user_id for Keycloak user ID reference.';

