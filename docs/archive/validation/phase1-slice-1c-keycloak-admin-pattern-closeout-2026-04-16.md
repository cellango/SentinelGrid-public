# Phase 1 Slice 1C Keycloak Admin Pattern Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Complete for the current narrowed launch scope  
**Owner:** Clement Ellango

## Purpose

Close the remaining production dependency on password-based Keycloak admin auth and remove the implicit service-account-to-password fallback from IAM runtime paths.

## Code Areas Closed

- `backend/agents/iam_agent/app/core/config.py`
- `backend/agents/iam_agent/app/services/keycloak_client.py`
- `backend/agents/iam_agent/app/services/keycloak_admin_client.py`
- `backend/agents/iam_agent/app/services/keycloak_admin_factory.py`
- `backend/agents/iam_agent/app/services/keycloak_seeder.py`

## What Changed

1. Production config now requires `KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT=true`.
2. Production config now requires `KEYCLOAK_ADMIN_CLIENT_ID` and `KEYCLOAK_ADMIN_CLIENT_SECRET`.
3. A shared runtime resolver now determines the Keycloak admin auth mode once and removes the old “try service account, else silently drop to password grant” behavior.
4. `KeycloakClient`, `KeycloakRoleClient`, `KeycloakAdminClient`, and the shared Keycloak admin factory now all use the same resolved auth contract.
5. Seeder REST token acquisition now uses the same resolved runtime auth contract instead of unconditionally using `admin-cli` password grant.
6. Legacy admin-account recovery remains explicit non-production recovery behavior only and is no longer part of the normal production runtime path.

## Verification Evidence

### Regression Tests

- `pytest backend/agents/iam_agent/tests/test_config_security.py backend/agents/iam_agent/tests/test_service_client_security.py backend/agents/iam_agent/tests/test_admin_auth_runtime.py -q`
  - result: `24` tests passed
- `pytest backend/agents/iam_agent/tests/test_keycloak_admin_client.py -q`
  - result: `20` tests passed

### Source Sweep Evidence

- `rg -n 'if .*KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT.*KEYCLOAK_ADMIN_CLIENT_SECRET|if self\\.use_service_account and self\\.admin_client_secret|if settings\\.KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT and settings\\.KEYCLOAK_ADMIN_CLIENT_SECRET' backend/agents/iam_agent/app/core/config.py backend/agents/iam_agent/app/services/keycloak_client.py backend/agents/iam_agent/app/services/keycloak_admin_client.py backend/agents/iam_agent/app/services/keycloak_admin_factory.py backend/agents/iam_agent/app/services/keycloak_seeder.py`
  - result: no matches
- `rg -n 'admin-cli|grant_type.*password' backend/agents/iam_agent/app/core/config.py backend/agents/iam_agent/app/services/keycloak_client.py backend/agents/iam_agent/app/services/keycloak_admin_client.py backend/agents/iam_agent/app/services/keycloak_admin_factory.py backend/agents/iam_agent/app/services/keycloak_seeder.py`
  - remaining matches are limited to:
    - the non-production password-mode template in `app/core/config.py`
    - explicit non-production recovery helpers in `app/services/keycloak_seeder.py`
    - seeded user-login verification in `app/services/keycloak_seeder.py`

## Break-Glass Boundary

Break-glass admin-account recovery is now explicitly separated from runtime service auth:

- runtime IAM admin operations resolve auth through the shared service-account-first contract
- production rejects password-based Keycloak admin runtime auth
- seeder recovery helpers that still reference `admin-cli` password grant are fenced to non-production password mode and are no longer a production runtime path

## Exit Decision

`Slice 1C` is closed for the current narrowed launch scope.

Production IAM runtime auth no longer depends on password-based Keycloak admin patterns. Phase 1 should continue with `Slice 1D`.
