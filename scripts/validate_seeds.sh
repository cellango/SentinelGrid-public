#!/usr/bin/env bash
set -euo pipefail

# Post-seed smoke checks to ensure expected demo/global data is present.
# Usage: DB_URL=postgresql://sg:sg@localhost:5432/sg ./scripts/validate_seeds.sh

DB_URL=${DB_URL:-postgresql://sg:sg@localhost:5432/sg}

psql_cmd() {
  psql "$DB_URL" -At -F $'\t' -v ON_ERROR_STOP=1 -c "$1"
}

echo "🔍 Validating seeds against ${DB_URL}"

# Plan tiers
echo "• Checking plan_tier for demo tenants and sg_admin..."
plan_rows=$(psql_cmd "SELECT slug, plan_tier FROM tenants WHERE slug IN ('demo','demo2','demo_protect','sg_admin') ORDER BY slug;")
expected_plan_rows=$'demo\tprotect_defend_comply\ndemo2\tprotect_defend\ndemo_protect\tprotect\nsg_admin\tprotect_defend_comply'
if [[ "$plan_rows" != "$expected_plan_rows" ]]; then
  echo "❌ plan_tier mismatch:"
  echo "$plan_rows"
  exit 1
fi

# Scans
echo "• Checking scans count..."
scans_demo=$(psql_cmd "SELECT COUNT(*) FROM scans WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo');")
scans_demo2=$(psql_cmd "SELECT COUNT(*) FROM scans WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo2');")
if [[ "$scans_demo" -lt 4 || "$scans_demo2" -lt 4 ]]; then
  echo "❌ scan counts unexpected (demo=$scans_demo, demo2=$scans_demo2, expected >=4 each)"
  exit 1
fi

# Compliance reports (only demo should have them)
echo "• Checking compliance reports for demo..."
reports_demo=$(psql_cmd "SELECT COUNT(*) FROM reporting.reports WHERE tenant_id::text = (SELECT id::text FROM tenants WHERE slug='demo');")
if [[ "$reports_demo" -lt 6 ]]; then
  echo "❌ compliance reports count unexpected for demo (got $reports_demo, expected >=6)"
  exit 1
fi
reports_demo2=$(psql_cmd "SELECT COUNT(*) FROM reporting.reports WHERE tenant_id::text = (SELECT id::text FROM tenants WHERE slug='demo2');")
if [[ "$reports_demo2" -ne 0 ]]; then
  echo "❌ demo2 should not have compliance reports (found $reports_demo2)"
  exit 1
fi

# Alerts
echo "• Checking alerts counts..."
alerts_demo=$(psql_cmd "SELECT COUNT(*) FROM security_ops.alerts WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo');")
alerts_demo2=$(psql_cmd "SELECT COUNT(*) FROM security_ops.alerts WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo2');")
alerts_protect=$(psql_cmd "SELECT COUNT(*) FROM security_ops.alerts WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo_protect');")
if [[ "$alerts_demo" -lt 3 || "$alerts_demo2" -lt 3 || "$alerts_protect" -lt 2 ]]; then
  echo "❌ alert counts unexpected (demo=$alerts_demo, demo2=$alerts_demo2, demo_protect=$alerts_protect; expected >=3, >=3, >=2)"
  exit 1
fi

# Personas/entitlements and IAM catalog
echo "• Checking user_entitlements and IAM catalog counts..."
ents_demo=$(psql_cmd "SELECT COUNT(*) FROM user_entitlements WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo');")
ents_demo2=$(psql_cmd "SELECT COUNT(*) FROM user_entitlements WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo2');")
ents_protect=$(psql_cmd "SELECT COUNT(*) FROM user_entitlements WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo_protect');")
if [[ "$ents_demo" -lt 10 || "$ents_demo2" -lt 8 || "$ents_protect" -lt 5 ]]; then
  echo "❌ entitlement counts unexpected (demo=$ents_demo, demo2=$ents_demo2, demo_protect=$ents_protect; expected >=10, >=8, >=5)"
  exit 1
fi

apps_demo=$(psql_cmd "SELECT COUNT(*) FROM apps WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo');")
apps_demo2=$(psql_cmd "SELECT COUNT(*) FROM apps WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo2');")
apps_protect=$(psql_cmd "SELECT COUNT(*) FROM apps WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo_protect');")
if [[ "$apps_demo" -lt 4 || "$apps_demo2" -lt 3 || "$apps_protect" -lt 3 ]]; then
  echo "❌ app counts unexpected (demo=$apps_demo, demo2=$apps_demo2, demo_protect=$apps_protect; expected >=4, >=3, >=3)"
  exit 1
fi

ap_demo=$(psql_cmd "SELECT COUNT(*) FROM access_profiles WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo');")
ap_demo2=$(psql_cmd "SELECT COUNT(*) FROM access_profiles WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo2');")
ap_protect=$(psql_cmd "SELECT COUNT(*) FROM access_profiles WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo_protect');")
if [[ "$ap_demo" -lt 3 || "$ap_demo2" -lt 2 || "$ap_protect" -lt 2 ]]; then
  echo "❌ access profile counts unexpected (demo=$ap_demo, demo2=$ap_demo2, demo_protect=$ap_protect; expected >=3, >=2, >=2)"
  exit 1
fi

assets_demo=$(psql_cmd "SELECT COUNT(*) FROM assets WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo');")
assets_demo2=$(psql_cmd "SELECT COUNT(*) FROM assets WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo2');")
assets_protect=$(psql_cmd "SELECT COUNT(*) FROM assets WHERE tenant_id = (SELECT id FROM tenants WHERE slug='demo_protect');")
if [[ "$assets_demo" -lt 3 || "$assets_demo2" -lt 2 || "$assets_protect" -lt 2 ]]; then
  echo "❌ device/asset counts unexpected (demo=$assets_demo, demo2=$assets_demo2, demo_protect=$assets_protect; expected >=3, >=2, >=2)"
  exit 1
fi

# Global catalog sanity
echo "• Checking global catalog (playbooks/detections/templates) in sg_admin..."
sg_admin_id=$(psql_cmd "SELECT id FROM tenants WHERE slug='sg_admin';")
playbooks_count=$(psql_cmd "SELECT COUNT(*) FROM public.playbooks WHERE tenant_id = '$sg_admin_id' AND is_builtin = true;")
det_rules_count=$(psql_cmd "SELECT COUNT(*) FROM security_ops.detection_rules WHERE tenant_id = '$sg_admin_id' AND is_builtin = true;")
templates_count=$(psql_cmd "SELECT COUNT(*) FROM reporting.report_templates WHERE tenant_id = '$sg_admin_id';")
global_apps=$(psql_cmd "SELECT COUNT(*) FROM apps WHERE tenant_id = '$sg_admin_id';")
global_access_profiles=$(psql_cmd "SELECT COUNT(*) FROM access_profiles WHERE tenant_id = '$sg_admin_id';")
if [[ "$playbooks_count" -lt 30 || "$det_rules_count" -lt 90 || "$templates_count" -lt 4 || "$global_apps" -lt 3 || "$global_access_profiles" -lt 3 ]]; then
  echo "❌ global catalog counts unexpected (playbooks=$playbooks_count, detections=$det_rules_count, templates=$templates_count, apps=$global_apps, access_profiles=$global_access_profiles; expected >=30, >=90, >=4, >=3, >=3)"
  exit 1
fi

echo "✅ Seed validation passed."
