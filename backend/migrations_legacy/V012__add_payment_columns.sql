-- Add payment-related columns to customers table
ALTER TABLE customers
ADD COLUMN IF NOT EXISTS payment_status TEXT DEFAULT 'pending', -- pending, paid, failed, cancelled
ADD COLUMN IF NOT EXISTS billing_period TEXT, -- monthly, yearly
ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
ADD COLUMN IF NOT EXISTS stripe_payment_method_id TEXT,
ADD COLUMN IF NOT EXISTS subscription_start_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS subscription_end_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_payment_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS next_payment_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS payment_amount_cents INTEGER, -- Amount in cents
ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'usd';

-- Add index for payment status lookups
CREATE INDEX IF NOT EXISTS idx_customers_payment_status ON customers(payment_status);
CREATE INDEX IF NOT EXISTS idx_customers_stripe_customer_id ON customers(stripe_customer_id);

