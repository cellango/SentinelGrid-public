-- Migration: Add signup_completed field to customers table
-- Purpose: Track whether a customer has completed the full signup wizard
-- This allows us to redirect users back to signup if account creation failed partway

ALTER TABLE customers 
ADD COLUMN IF NOT EXISTS signup_completed BOOLEAN DEFAULT FALSE;

-- Update existing customers to mark them as completed (they're already set up)
UPDATE customers 
SET signup_completed = TRUE 
WHERE signup_completed IS NULL OR signup_completed = FALSE;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_customers_signup_completed ON customers(signup_completed);

COMMENT ON COLUMN customers.signup_completed IS 'Whether the customer has completed all signup wizard steps. If FALSE, user should be redirected to signup page to complete setup.';

