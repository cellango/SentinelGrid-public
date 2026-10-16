-- Migration: Add employee_count to customers table
-- Date: 2025-01-28
-- Purpose: Support employee count collection for tier determination in signup flow
-- Note: compliance_required column already exists in migration 009_realm_architecture.sql

-- Add employee_count column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'customers' AND column_name = 'employee_count'
    ) THEN
        ALTER TABLE customers ADD COLUMN employee_count INTEGER;
        COMMENT ON COLUMN customers.employee_count IS 'Number of employees in the company (used for tier determination)';
    END IF;
END $$;

-- Create index on employee_count for tier determination queries
CREATE INDEX IF NOT EXISTS idx_customers_employee_count ON customers(employee_count);

