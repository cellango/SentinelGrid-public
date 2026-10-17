"""Explicit source-review route selection, not deployment qualification.

Unlisted operations are unavailable even when added to an otherwise reviewed
module. HTTP/model/body/deployment flags cannot extend this constant. Domain
handlers still own authentication, tenant/role checks and transactional audit.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.routing import APIRoute
from app.api.request_context import get_current_request_context

logger = logging.getLogger(__name__)

# router identity, method, full path, endpoint module and endpoint name.
REVIEWED_SOURCE_ROUTES = frozenset([
    ('access_requests.router', 'GET', '/api/v1/access-requests', 'app.api.access_requests', 'list_access_requests'),
    ('access_requests.router', 'GET', '/api/v1/access-requests/{request_id}', 'app.api.access_requests', 'get_access_request'),
    ('access_requests.router', 'GET', '/api/v1/access-requests/{request_id}/history', 'app.api.access_requests', 'get_access_request_history'),
    ('access_requests.router', 'POST', '/api/v1/access-requests', 'app.api.access_requests', 'create_access_request'),
    ('access_requests.router', 'POST', '/api/v1/access-requests/{request_id}/cancel', 'app.api.access_requests', 'cancel_access_request'),
    ('access_requests.router', 'POST', '/api/v1/access-requests/{request_id}/review', 'app.api.access_requests', 'review_access_request'),
    ('ai_editor.router', 'POST', '/api/v1/ai/editor/analyze', 'app.api.ai_editor', 'unsupported'),
    ('ai_editor.router', 'POST', '/api/v1/ai/editor/explain', 'app.api.ai_editor', 'explain'),
    ('ai_editor.router', 'POST', '/api/v1/ai/editor/generate', 'app.api.ai_editor', 'generate'),
    ('ai_editor.router', 'POST', '/api/v1/ai/editor/suggest', 'app.api.ai_editor', 'unsupported'),
    ('ai_editor.router', 'POST', '/api/v1/ai/editor/validate-nl', 'app.api.ai_editor', 'unsupported'),
    ('auth.public_router', 'POST', '/api/v1/auth/reset-password-direct', 'app.api.auth', 'reset_password_direct'),
    ('auth.router', 'POST', '/internal/iam/auth/introspect', 'app.api.auth', 'introspect_token'),
    ('auth.router', 'POST', '/internal/iam/auth/validate-token', 'app.api.auth', 'validate_token'),
    ('authorize.router', 'DELETE', '/api/v1/authorize/cache', 'app.api.authorize', 'clear_evaluation_cache'),
    ('authorize.router', 'POST', '/api/v1/authorize', 'app.api.authorize', 'authorize'),
    ('authorize.router', 'POST', '/api/v1/authorize/batch', 'app.api.authorize', 'authorize_batch'),
    ('authorize.router', 'POST', '/api/v1/authorize/user/entitlements', 'app.api.authorize', 'get_user_entitlements'),
    ('bulk_operations.router', 'DELETE', '/api/v1/entitlements/bulk', 'app.api.bulk_operations', 'bulk_delete_entitlements'),
    ('bulk_operations.router', 'POST', '/api/v1/entitlements/bulk', 'app.api.bulk_operations', 'bulk_create_entitlements'),
    ('bulk_operations.router', 'PUT', '/api/v1/entitlements/bulk', 'app.api.bulk_operations', 'bulk_update_entitlements'),
    ('entitlements.router', 'DELETE', '/api/v1/entitlements/{entitlement_id}', 'app.api.entitlements', 'delete_entitlement'),
    ('entitlements.router', 'GET', '/api/v1/entitlements', 'app.api.entitlements', 'list_entitlements'),
    ('entitlements.router', 'GET', '/api/v1/entitlements/{entitlement_id}', 'app.api.entitlements', 'get_entitlement'),
    ('entitlements.router', 'POST', '/api/v1/entitlements', 'app.api.entitlements', 'create_entitlement'),
    ('entitlements.router', 'PUT', '/api/v1/entitlements/{entitlement_id}', 'app.api.entitlements', 'update_entitlement'),
    ('governance.router', 'GET', '/api/v1/governance/campaigns', 'app.api.governance', 'list_campaigns'),
    ('governance.router', 'GET', '/api/v1/governance/campaigns/{campaign_id}', 'app.api.governance', 'get_campaign'),
    ('governance.router', 'GET', '/api/v1/governance/certifications', 'app.api.governance', 'list_certifications'),
    ('governance.router', 'GET', '/api/v1/governance/certifications/pending', 'app.api.governance', 'get_pending_certifications'),
    ('governance.router', 'POST', '/api/v1/governance/campaigns', 'app.api.governance', 'create_campaign'),
    ('governance.router', 'POST', '/api/v1/governance/campaigns/{campaign_id}/complete', 'app.api.governance', 'complete_campaign'),
    ('governance.router', 'POST', '/api/v1/governance/campaigns/{campaign_id}/start', 'app.api.governance', 'start_campaign'),
    ('governance.router', 'POST', '/api/v1/governance/certifications/bulk-certify', 'app.api.governance', 'bulk_certify'),
    ('governance.router', 'POST', '/api/v1/governance/certifications/{certification_id}/certify', 'app.api.governance', 'certify_entitlement'),
    ('governance.router', 'PUT', '/api/v1/governance/campaigns/{campaign_id}', 'app.api.governance', 'update_campaign'),
    ('iam_policies.router', 'DELETE', '/api/iam-portal/policies/{policy_id}', 'app.api.policies', 'delete_policy'),
    ('iam_policies.router', 'GET', '/api/iam-portal/policies', 'app.api.policies', 'list_policies'),
    ('iam_policies.router', 'GET', '/api/iam-portal/policies/bundles', 'app.api.policies', 'list_seed_bundles'),
    ('iam_policies.router', 'GET', '/api/iam-portal/policies/templates', 'app.api.policies', 'list_templates'),
    ('iam_policies.router', 'GET', '/api/iam-portal/policies/templates/list', 'app.api.policies', 'list_templates_v2'),
    ('iam_policies.router', 'GET', '/api/iam-portal/policies/{policy_id}', 'app.api.policies', 'get_policy'),
    ('iam_policies.router', 'GET', '/api/iam-portal/policies/{policy_id}/analyze', 'app.api.policies', 'analyze_policy'),
    ('iam_policies.router', 'POST', '/api/iam-portal/policies', 'app.api.policies', 'create_policy'),
    ('iam_policies.router', 'POST', '/api/iam-portal/policies/bundles/{policy_id}/clone', 'app.api.policies', 'clone_seed_bundle'),
    ('iam_policies.router', 'POST', '/api/iam-portal/policies/evaluate', 'app.api.policies', 'evaluate_policy'),
    ('iam_policies.router', 'POST', '/api/iam-portal/policies/generate', 'app.api.policies', 'generate_policy'),
    ('iam_policies.router', 'POST', '/api/iam-portal/policies/templates/{template_id}/create', 'app.api.policies', 'create_policy_from_template'),
    ('iam_policies.router', 'POST', '/api/iam-portal/policies/{policy_id}/approve', 'app.api.policies', 'approve_policy'),
    ('iam_policies.router', 'POST', '/api/iam-portal/policies/{policy_id}/explain', 'app.api.policies', 'explain_policy'),
    ('iam_policies.router', 'POST', '/api/iam-portal/policies/{policy_id}/reject', 'app.api.policies', 'reject_policy'),
    ('iam_policies.router', 'PUT', '/api/iam-portal/policies/{policy_id}', 'app.api.policies', 'update_policy'),
    ('itdr.router', 'POST', '/internal/iam/itdr/enforce', 'app.api.itdr', 'enforce_threat'),
    ('itdr.router', 'POST', '/internal/iam/itdr/enforce/batch', 'app.api.itdr', 'enforce_threats_batch'),
    ('nhi.router', 'DELETE', '/api/v1/nhi/service-accounts/{account_id}', 'app.api.nhi', 'delete_service_account'),
    ('nhi.router', 'GET', '/api/v1/nhi/service-accounts', 'app.api.nhi', 'list_service_accounts'),
    ('nhi.router', 'GET', '/api/v1/nhi/service-accounts/expiring', 'app.api.nhi', 'get_expiring_credentials'),
    ('nhi.router', 'GET', '/api/v1/nhi/service-accounts/{account_id}', 'app.api.nhi', 'get_service_account'),
    ('nhi.router', 'POST', '/api/v1/nhi/service-accounts', 'app.api.nhi', 'create_service_account'),
    ('nhi.router', 'POST', '/api/v1/nhi/service-accounts/{account_id}/activate', 'app.api.nhi', 'activate_service_account'),
    ('nhi.router', 'POST', '/api/v1/nhi/service-accounts/{account_id}/deactivate', 'app.api.nhi', 'deactivate_service_account'),
    ('nhi.router', 'POST', '/api/v1/nhi/service-accounts/{account_id}/rotate', 'app.api.nhi', 'rotate_credentials'),
    ('role_mappings.router', 'DELETE', '/api/v1/role-mappings/{pattern_id}', 'app.api.role_mappings', 'delete_role_pattern'),
    ('role_mappings.router', 'GET', '/api/v1/role-mappings', 'app.api.role_mappings', 'list_role_patterns'),
    ('role_mappings.router', 'GET', '/api/v1/role-mappings/{pattern_id}', 'app.api.role_mappings', 'get_role_pattern'),
    ('role_mappings.router', 'POST', '/api/v1/role-mappings', 'app.api.role_mappings', 'create_role_pattern'),
    ('role_mappings.router', 'POST', '/api/v1/role-mappings/sync/role', 'app.api.role_mappings', 'sync_role_to_users'),
    ('role_mappings.router', 'POST', '/api/v1/role-mappings/sync/role/{role_name}/revoke', 'app.api.role_mappings', 'revoke_role_entitlements'),
    ('role_mappings.router', 'POST', '/api/v1/role-mappings/sync/user', 'app.api.role_mappings', 'sync_user_roles'),
    ('role_mappings.router', 'PUT', '/api/v1/role-mappings/{pattern_id}', 'app.api.role_mappings', 'update_role_pattern'),
    ('scim.router', 'DELETE', '/api/v1/scim/v2/Groups/{group_id}', 'app.api.scim', 'group_scim'),
    ('scim.router', 'DELETE', '/api/v1/scim/v2/Users/{user_id}', 'app.api.scim', 'delete_user_scim'),
    ('scim.router', 'GET', '/api/v1/scim/v2/Groups', 'app.api.scim', 'groups_scim'),
    ('scim.router', 'GET', '/api/v1/scim/v2/Groups/{group_id}', 'app.api.scim', 'group_scim'),
    ('scim.router', 'GET', '/api/v1/scim/v2/ServiceProviderConfig', 'app.api.scim', 'get_service_provider_config'),
    ('scim.router', 'GET', '/api/v1/scim/v2/Users', 'app.api.scim', 'list_users_scim'),
    ('scim.router', 'GET', '/api/v1/scim/v2/Users/{user_id}', 'app.api.scim', 'get_user_scim'),
    ('scim.router', 'PATCH', '/api/v1/scim/v2/Groups/{group_id}', 'app.api.scim', 'group_scim'),
    ('scim.router', 'PATCH', '/api/v1/scim/v2/Users/{user_id}', 'app.api.scim', 'patch_user_scim'),
    ('scim.router', 'POST', '/api/v1/scim/v2/Bulk', 'app.api.scim', 'unsupported_scim'),
    ('scim.router', 'POST', '/api/v1/scim/v2/Groups', 'app.api.scim', 'groups_scim'),
    ('scim.router', 'POST', '/api/v1/scim/v2/Groups/.search', 'app.api.scim', 'unsupported_scim'),
    ('scim.router', 'POST', '/api/v1/scim/v2/Users', 'app.api.scim', 'create_user_scim'),
    ('scim.router', 'POST', '/api/v1/scim/v2/Users/.search', 'app.api.scim', 'unsupported_scim'),
    ('scim.router', 'PUT', '/api/v1/scim/v2/Groups/{group_id}', 'app.api.scim', 'group_scim'),
    ('scim.router', 'PUT', '/api/v1/scim/v2/Users/{user_id}', 'app.api.scim', 'update_user_scim'),
])


async def unavailable_source_route(context=Depends(get_current_request_context)):
    raise HTTPException(
        status_code=501,
        detail="This legacy IAM operation is unavailable pending source, data and action qualification",
    )


def include_source_router(app, router_id, router, *, prefix=""):
    """Mount explicit review operations and block other HTTP handlers before DI.

    Register reviewed routers before legacy aliases. Preserve route classes and
    original dependency contracts. Reject nested/non-HTTP surfaces and startup
    hooks instead of silently granting them the containing module's admission.
    """
    default_lifespan_type = type(APIRouter().lifespan_context)
    if (
        router.on_startup
        or router.on_shutdown
        or type(router.lifespan_context) is not default_lifespan_type
    ):
        raise ValueError("Router startup hooks need separate admission")
    if any(not isinstance(route, APIRoute) for route in router.routes):
        raise ValueError("Nested or non-HTTP routes need separate admission")
    if not hasattr(app.state, "iam_source_routes"):
        app.state.iam_source_routes = []
    records = app.state.iam_source_routes
    existing = {(r["method"], r["path"]): r for r in records if r["mounted"]}

    # Literal routes must precede parameter routes, including policy templates
    # versus /{policy_id}. Cross-router bulk routes register before grant IDs.
    def specificity(route):
        return tuple((1 if "{" in part else 0, part) for part in route.path.split("/"))

    for route in sorted(router.routes, key=specificity):
        path = prefix + route.path
        operations = [
            (
                router_id,
                method,
                path,
                route.endpoint.__module__,
                route.endpoint.__name__,
            )
            for method in sorted(route.methods)
        ]
        reviewed = all(operation in REVIEWED_SOURCE_ROUTES for operation in operations)
        collisions = [(op[1], path) for op in operations if (op[1], path) in existing]
        if collisions and reviewed:
            raise ValueError("Reviewed routes must precede aliases and cannot collide")
        if collisions:
            # Do not let a legacy alias shadow a reviewed canonical handler or
            # add unreviewed methods through a partially overlapping route.
            for op in operations:
                records.append(
                    dict(
                        router_id=router_id,
                        method=op[1],
                        path=path,
                        endpoint=op[4],
                        reviewed=False,
                        mounted=False,
                        disposition="legacy_alias_not_mounted",
                    )
                )
            continue
        single = APIRouter()
        single.routes.append(route)  # No mutation of the reusable source router.
        app.include_router(
            single,
            prefix=prefix,
            dependencies=[] if reviewed else [Depends(unavailable_source_route)],
        )
        for op in operations:
            record = dict(
                router_id=router_id,
                method=op[1],
                path=path,
                endpoint=op[4],
                reviewed=reviewed,
                mounted=True,
                disposition="bounded_source_checks"
                if reviewed
                else "blocked_before_handler_dependencies",
            )
            records.append(record)
            existing[(op[1], path)] = record


@asynccontextmanager
async def source_review_lifespan(app):
    """No automatic bootstrap, schema creation, directory mutation or jobs."""
    logger.info(
        "IAM source review: automatic provider seeding and legacy jobs are unavailable"
    )
    yield
    logger.info("IAM source review stopped")
