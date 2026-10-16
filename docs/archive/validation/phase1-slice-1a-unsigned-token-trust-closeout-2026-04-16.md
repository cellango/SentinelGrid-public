# Phase 1 Slice 1A Unsigned Token Trust Closeout

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 16, 2026  
**Status:** Complete on April 16, 2026  
**Gate Alignment:** `G-03`  
**Purpose:** Record the repo-backed evidence that IAM public auth paths no longer trust unsigned JWT payload data for the narrowed launch scope

## Scope

This closeout covers the launch-scope IAM public auth and callback paths in:

- `backend/agents/iam_agent/app/api/auth.py`
- `backend/agents/iam_agent/app/api/gateway.py`
- `backend/agents/iam_agent/app/services/token_validator.py`

## Code Changes Closed In This Slice

- `auth.py` now validates tokens before using claims in `_direct_login`, `/logout`, `/refresh`, `/me`, and `get_customer_id_from_token`
- `gateway.py` now uses validated access-token and id-token payloads for issuer, audience, and nonce handling instead of re-decoding those tokens unsigned
- `token_validator.py` no longer uses unsigned PyJWT decode to discover the realm; it only parses the untrusted payload bytes to locate the candidate issuer before signature validation
- IAM-side outbound calls in these paths now honor `settings.KEYCLOAK_VERIFY_TLS` instead of forcing `verify=False`

## Verification Evidence

Verification commands:

```bash
rg -n "verify_signature=False|jwt\\.decode\\(|options=\\{\\\"verify_signature\\\": False\\}" backend/agents/iam_agent/app -g '*.py'
pytest backend/agents/iam_agent/tests/test_auth_api.py backend/agents/iam_agent/tests/test_gateway_state_binding.py -q
pytest backend/agents/iam_agent/tests/test_route_transport_security.py -q
```

Observed results on April 16, 2026:

- the `rg` scan returned no remaining unsigned-decode matches in `backend/agents/iam_agent/app`
- `pytest backend/agents/iam_agent/tests/test_auth_api.py backend/agents/iam_agent/tests/test_gateway_state_binding.py -q` passed with `20 passed`
- `pytest backend/agents/iam_agent/tests/test_route_transport_security.py -q` passed with `5 passed`

## Regression Coverage Added Or Updated

- forged bearer token rejected on `/api/v1/auth/me`
- manipulated `tenant_id` in token payload ignored in favor of the validator-normalized tenant
- `/logout` derives the Keycloak logout realm from the validated refresh token
- `/refresh` rejects an invalid access token returned by the identity provider
- OIDC callback rejects invalid token audience
- OIDC callback rejects invalid nonce

## Gate Result

`G-03` can be marked `Pass` for the current narrowed launch scope.

This closes the unsigned-token-trust objective in Phase 1 Slice 1A. It does **not** close the rest of Phase 1.

## Remaining Phase 1 Work

The following slices remain open:

- `Slice 1B`: finish the BFF and session boundary cleanup
- `Slice 1C`: close Keycloak admin/runtime auth pattern risk
- `Slice 1D`: finish frontend security header and proxy cleanup
