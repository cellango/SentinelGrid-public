-- Migration: Add simplified pricing fields to customers and tenants
-- Date: 2025-01-29
-- Purpose: Support new package-based pricing (Protect vs Protect & Comply) with user bands

-- Add package_name to customers table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'customers' AND column_name = 'package_name'
    ) THEN
        ALTER TABLE customers ADD COLUMN package_name VARCHAR(50);
        COMMENT ON COLUMN customers.package_name IS 'Package name: protect or protect_comply';
    END IF;
END $$;

-- Add user_band to customers table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'customers' AND column_name = 'user_band'
    ) THEN
        ALTER TABLE customers ADD COLUMN user_band VARCHAR(20);
        COMMENT ON COLUMN customers.user_band IS 'User band: 1-25, 26-50, 51-100, 101-250, 250+';
    END IF;
END $$;

-- Add user_count to customers (rename from employee_count for clarity, keep both for migration)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'customers' AND column_name = 'user_count'
    ) THEN
        ALTER TABLE customers ADD COLUMN user_count INTEGER;
        COMMENT ON COLUMN customers.user_count IS 'Actual user count (used to determine user_band)';
    END IF;
END $$;

-- Migrate existing data: copy employee_count to user_count
UPDATE customers SET user_count = employee_count WHERE user_count IS NULL AND employee_count IS NOT NULL;

-- Add package_name to tenants table (optional, for reference)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tenants' AND column_name = 'package_name'
    ) THEN
        ALTER TABLE tenants ADD COLUMN package_name VARCHAR(50);
        COMMENT ON COLUMN tenants.package_name IS 'Package name: protect or protect_comply';
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_customers_package_name ON customers(package_name);
CREATE INDEX IF NOT EXISTS idx_customers_user_band ON customers(user_band);

