#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

require_rg() {
  local pattern="$1"
  local file="$2"
  local error_message="$3"
  if ! rg -q "$pattern" "$file"; then
    fail "$error_message"
  fi
}

SUPPORT_RUNBOOK="$REPO_ROOT/docs/archive/operations/production-support-and-incident-response.md"
TRUST_PACK="$REPO_ROOT/docs/PHASE5_CUSTOMER_TRUST_PACK_2026-04-16.md"
SECURITY_FAQ="$REPO_ROOT/docs/PHASE5_SECURITY_REVIEW_FAQ_2026-04-16.md"
OWNER_MATRIX="$REPO_ROOT/docs/PRODUCTION_OWNER_MATRIX_2026-04-15.md"
TRUST_PAGE="$REPO_ROOT/frontend/src/app/(marketing)/trust/page.tsx"

echo "Verifying launch support operating model alignment..."

require_rg 'one-person operating model|founder-led' "$SUPPORT_RUNBOOK" "Support runbook does not describe the actual founder-led operating model"
require_rg 'support@sentinelgrid\.ai' "$SUPPORT_RUNBOOK" "Support runbook is missing the primary support contact path"
require_rg 'staffed 24/7 SOC|blanket SLA' "$SUPPORT_RUNBOOK" "Support runbook is missing the no-overclaim support coverage boundary"
require_rg 'First Customer Activation Workflow' "$SUPPORT_RUNBOOK" "Support runbook is missing the first customer activation workflow"
require_rg 'Support Intake Record' "$SUPPORT_RUNBOOK" "Support runbook is missing the support intake template"
require_rg 'Communication Templates' "$SUPPORT_RUNBOOK" "Support runbook is missing communication templates"

require_rg 'support@sentinelgrid\.ai' "$TRUST_PACK" "Trust pack is missing the support contact path"
require_rg 'founder-led' "$TRUST_PACK" "Trust pack does not reflect the founder-led support model"
require_rg '24/7 SOC|blanket SLA' "$TRUST_PACK" "Trust pack is missing the support boundary disclaimer"

require_rg 'support@sentinelgrid\.ai' "$SECURITY_FAQ" "Security FAQ is missing the support contact path"
require_rg 'founder-led' "$SECURITY_FAQ" "Security FAQ does not reflect the founder-led support model"
require_rg '24/7 SOC|blanket SLA' "$SECURITY_FAQ" "Security FAQ is missing the support boundary disclaimer"

require_rg 'Clement Ellango' "$OWNER_MATRIX" "Owner matrix does not identify the named launch owner"
require_rg 'Support Lead' "$OWNER_MATRIX" "Owner matrix is missing support ownership"

require_rg 'support@sentinelgrid\.ai' "$TRUST_PAGE" "Trust page is missing the support contact path"
require_rg 'founder-led' "$TRUST_PAGE" "Trust page does not reflect the founder-led support model"
require_rg '24/7 SOC|blanket SLA' "$TRUST_PAGE" "Trust page is missing the support boundary disclaimer"

echo "PASS: launch support, trust, and incident-response materials are aligned to the current founder-led operating model."
