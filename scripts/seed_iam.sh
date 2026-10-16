#!/usr/bin/env bash
set -euo pipefail

# Seed IAM personas/birthrights/policies for each tenant (idempotent).
# Usage: DB_URL=postgresql://sg:sg@localhost:5432/sg TENANTS="demo_protect demo_protect_defend demo" ./scripts/seed_iam.sh

DB_URL=${DB_URL:-postgresql://sg:sg@localhost:5432/sg}
TENANTS=${TENANTS:-demo}

for slug in $TENANTS; do
  echo "👥 Seeding IAM for tenant slug=${slug}"
  PGPASSWORD=${DB_PASSWORD:-} psql "$DB_URL" -v ON_ERROR_STOP=1 <<SQL
DO \$do\$
DECLARE
  t UUID;
  cust UUID;
  ap_birthright UUID := uuid_generate_v4();
  pol_signon UUID := uuid_generate_v4();
  pol_access UUID := uuid_generate_v4();
  pol_approval UUID := uuid_generate_v4();
  pol_sod UUID := uuid_generate_v4();
  pol_authz UUID := uuid_generate_v4();
BEGIN
  SELECT id, customer_id INTO t, cust FROM tenants WHERE slug = '${slug}' LIMIT 1;
  IF t IS NULL THEN
    RAISE EXCEPTION 'Tenant slug % not found', '${slug}';
  END IF;

  -- Birthright / default access profile (upsert by name)
  INSERT INTO access_profiles (id, tenant_id, name, display_name, description, is_default, is_system, is_birthright, scope)
  VALUES (ap_birthright, t, 'default_birthright', 'Default Birthright', 'Baseline access for all users', true, false, true, 'all_users')
  ON CONFLICT (tenant_id, name) DO UPDATE
    SET is_default = EXCLUDED.is_default,
        is_birthright = EXCLUDED.is_birthright,
        description = EXCLUDED.description,
        updated_at = now();

  IF '${slug}' = 'sg_admin' THEN
    -- Clean out legacy tenant-level seeds to avoid duplicate bundle names
    DELETE FROM policies
    WHERE tenant_id = t
      AND name IN ('signon-baseline','access-baseline','approval-baseline','sod-baseline','authorization-baseline','iam-baseline');

    -- Global policy bundles live only in sg_admin
    INSERT INTO policies (id, tenant_id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by, is_template, approval_required, approval_status)
    VALUES
      (
        pol_signon, t,
        'global-signon-baseline',
        'Global Sign-on Baseline',
        'Require MFA for risky sign-ins and block inactive accounts.',
        'signon',
        'tenant',
        t,
        jsonb_build_object('version','1.0','rules',jsonb_build_array(
          jsonb_build_object('id','mfa-risks','actions',jsonb_build_array('mfa'),'conditions',jsonb_build_array(jsonb_build_object('attribute','risk_level','operator','in','value',jsonb_build_array('medium','high')))),
          jsonb_build_object('id','block-inactive','actions',jsonb_build_array('deny'),'conditions',jsonb_build_array(jsonb_build_object('attribute','last_login_days','operator','>','value',90)))
        )),
        true,
        10,
        'seed',
        true,
        false,
        'approved'
      ),
      (
        pol_access, t,
        'global-access-baseline',
        'Global Access Guardrails',
        'Enforce least-privilege bundles for core apps.',
        'access',
        'tenant',
        t,
        jsonb_build_object('version','1.0','rules',jsonb_build_array(
          jsonb_build_object('id','allow-standard','actions',jsonb_build_array('allow'),'conditions',jsonb_build_array(jsonb_build_object('attribute','access_profile','operator','in','value',jsonb_build_array('standard-employee','default_birthright')))),
          jsonb_build_object('id','privileged-mfa','actions',jsonb_build_array('mfa'),'conditions',jsonb_build_array(jsonb_build_object('attribute','is_privileged','operator','==','value',true)))
        )),
        true,
        20,
        'seed',
        true,
        false,
        'approved'
      ),
      (
        pol_approval, t,
        'global-approval-baseline',
        'Global Approval Flow',
        'Manager approval for high-risk app access.',
        'approval',
        'tenant',
        t,
        jsonb_build_object('version','1.0','rules',jsonb_build_array(
          jsonb_build_object('id','manager-approve','actions',jsonb_build_array('require_manager_approval'),'conditions',jsonb_build_array(jsonb_build_object('attribute','entitlement_risk','operator','in','value',jsonb_build_array('high','critical'))))
        )),
        true,
        30,
        'seed',
        true,
        false,
        'approved'
      ),
      (
        pol_sod, t,
        'global-sod-baseline',
        'Global SoD Guardrails',
        'Prevent toxic combinations of access.',
        'sod',
        'tenant',
        t,
        jsonb_build_object('version','1.0','rules',jsonb_build_array(
          jsonb_build_object('id','no-admin-approver','actions',jsonb_build_array('deny'),'conditions',jsonb_build_array(
            jsonb_build_object('attribute','entitlements','operator','contains_all','value',jsonb_build_array('admin','approver'))
          ))
        )),
        true,
        40,
        'seed',
        true,
        false,
        'approved'
      ),
      (
        pol_authz, t,
        'global-authorization-baseline',
        'Global Authorization Baseline',
        'Seeded sg_admin authorization policy bundle.',
        'authorization',
        'tenant',
        t,
        jsonb_build_object('rules', jsonb_build_array()),
        true,
        50,
        'seed',
        true,
        false,
        'approved'
      )
    ON CONFLICT (tenant_id, name) DO UPDATE
      SET policy_type      = EXCLUDED.policy_type,
          display_name     = EXCLUDED.display_name,
          description      = EXCLUDED.description,
          scope            = EXCLUDED.scope,
          scope_id         = EXCLUDED.scope_id,
          policy_data      = EXCLUDED.policy_data,
          is_active        = EXCLUDED.is_active,
          priority         = EXCLUDED.priority,
          approval_required= EXCLUDED.approval_required,
          approval_status  = EXCLUDED.approval_status,
          is_template      = EXCLUDED.is_template,
          updated_at       = now();
  ELSE
    -- Clean up previously seeded tenant policies (now only global)
    DELETE FROM policies
    WHERE tenant_id = t
      AND name IN ('signon-baseline','access-baseline','approval-baseline','sod-baseline','authorization-baseline','iam-baseline');
  END IF;
END \$do\$;
SQL
  echo "✅ IAM seeded for ${slug}"
done
