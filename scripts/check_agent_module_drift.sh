#!/usr/bin/env bash
set -euo pipefail

legacy_references=(
  "backend/services/siem_agent"
  "backend/services/entitlement_agent"
  "backend/services/ai_enrichment_agent"
  "services/siem_agent"
  "services/entitlement_agent"
  "services/ai_enrichment_agent"
  "http://entitlement_agent:"
  "http://ai_enrichment_agent:"
)

legacy_dockerfiles=(
  "backend/services/siem_agent/Dockerfile"
  "backend/services/entitlement_agent/Dockerfile"
  "backend/services/ai_enrichment_agent/Dockerfile"
)

production_docs=(
  "docs/DOCKER_STATUS_SUMMARY.md"
  "docs/archive/reference/infrastructure/docker-kubernetes-readiness.md"
  "docs/archive/reference/infrastructure/ports.md"
)

allowed_globs=(
  "--glob" "!docs/**"
  "--glob" "!**/README_DEPRECATED.md"
  "--glob" "!backend/services/siem_agent/**"
  "--glob" "!backend/services/entitlement_agent/**"
  "--glob" "!backend/services/ai_enrichment_agent/**"
  "--glob" "!scripts/check_agent_module_drift.sh"
  "--glob" "!scripts/check_agent_legacy_cleanup_readiness.py"
  "--glob" "!scripts/check_agent_runtime_compose_wiring.py"
  "--glob" "!scripts/supply_chain/verify_launch_scope_agent_targets.py"
  "--glob" "!node_modules/**"
  "--glob" "!frontend/.next/**"
  "--glob" "!frontend/out/**"
  "--glob" "!coverage/**"
  "--glob" "!.git/**"
)

failed=0
for legacy_reference in "${legacy_references[@]}"; do
  if rg --fixed-strings --line-number "${allowed_globs[@]}" "$legacy_reference" .; then
    echo "Forbidden active reference found for legacy agent path or service URL: $legacy_reference" >&2
    failed=1
  fi
done

for legacy_dockerfile in "${legacy_dockerfiles[@]}"; do
  if [[ -f "$legacy_dockerfile" ]] && ! rg --fixed-strings --quiet "DO_NOT_BUILD_LEGACY_SERVICE_TREE" "$legacy_dockerfile"; then
    echo "Legacy Dockerfile is not quarantined: $legacy_dockerfile" >&2
    failed=1
  fi
done

for production_doc in "${production_docs[@]}"; do
  [[ -f "$production_doc" ]] || continue
  for legacy_reference in "${legacy_references[@]}"; do
    if rg --fixed-strings --line-number "$legacy_reference" "$production_doc"; then
      echo "Production doc still presents legacy agent path or service URL: $production_doc -> $legacy_reference" >&2
      failed=1
    fi
  done
done

exit "$failed"
