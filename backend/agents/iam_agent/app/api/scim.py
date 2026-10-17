"""Partial read-only SCIM User adapter; provisioning and Groups are blocked."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from app.core.database import IAMSessionLocal, IAMDatabaseNotConfigured
from sg_core.tenant_session import tenant_session
from app.services.scim_service import (
    ERROR_SCHEMA,
    SCIMContext,
    SCIMError,
    SCIMService,
    verify_scim_token,
)


class SCIMJSONResponse(JSONResponse):
    media_type = "application/scim+json"


class SCIMRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def scim_handler(request):
            try:
                if len(request.headers.getlist("authorization")) > 1:
                    raise SCIMError(
                        401,
                        "Ambiguous SCIM authorization",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                response = await handler(request)
            except (HTTPException, RequestValidationError) as error:
                status = error.status_code if isinstance(error, HTTPException) else 400
                detail = (
                    error.detail
                    if isinstance(error, HTTPException)
                    and isinstance(error.detail, str)
                    else "Invalid SCIM request"
                )
                content = dict(
                    schemas=[ERROR_SCHEMA], status=str(status), detail=detail
                )
                scim_type = getattr(error, "scim_type", None)
                if scim_type:
                    content["scimType"] = scim_type
                response = SCIMJSONResponse(
                    content, status_code=status, headers=getattr(error, "headers", None)
                )
            response.headers["Cache-Control"] = "no-store"
            return response

        return scim_handler


router = APIRouter(
    prefix="/api/v1/scim/v2",
    tags=["scim"],
    route_class=SCIMRoute,
    default_response_class=SCIMJSONResponse,
)


def get_scim_session(context: SCIMContext = Depends(verify_scim_token)):
    try:
        with tenant_session(IAMSessionLocal, context.tenant_id) as db:
            yield db
    except IAMDatabaseNotConfigured as error:
        raise SCIMError(503, "SCIM audit database is not configured") from error


@router.get("/Users")
async def list_users_scim(
    request: Request,
    context: SCIMContext = Depends(verify_scim_token),
    db: Session = Depends(get_scim_session),
):
    return await SCIMService(db, context).handle(
        "list_users", query=request.query_params.multi_items()
    )


@router.get("/Users/{user_id}")
async def get_user_scim(
    user_id: str,
    request: Request,
    context: SCIMContext = Depends(verify_scim_token),
    db: Session = Depends(get_scim_session),
):
    return await SCIMService(db, context).handle(
        "get_user", identity=user_id, query=request.query_params.multi_items()
    )


@router.post("/Users")
async def create_user_scim(
    context: SCIMContext = Depends(verify_scim_token),
    db: Session = Depends(get_scim_session),
):
    return await SCIMService(db, context).handle("create_user")


@router.put("/Users/{user_id}")
async def update_user_scim(
    user_id: str,
    context: SCIMContext = Depends(verify_scim_token),
    db: Session = Depends(get_scim_session),
):
    return await SCIMService(db, context).handle("replace_user", identity=user_id)


@router.patch("/Users/{user_id}")
async def patch_user_scim(
    user_id: str,
    context: SCIMContext = Depends(verify_scim_token),
    db: Session = Depends(get_scim_session),
):
    return await SCIMService(db, context).handle("patch_user", identity=user_id)


@router.delete("/Users/{user_id}")
async def delete_user_scim(
    user_id: str,
    context: SCIMContext = Depends(verify_scim_token),
    db: Session = Depends(get_scim_session),
):
    return await SCIMService(db, context).handle("delete_user", identity=user_id)


@router.api_route("/Groups", methods=["GET", "POST"])
async def groups_scim(
    request: Request,
    context: SCIMContext = Depends(verify_scim_token),
    db: Session = Depends(get_scim_session),
):
    return await SCIMService(db, context).handle("groups_" + request.method.lower())


@router.api_route("/Groups/{group_id}", methods=["GET", "PUT", "PATCH", "DELETE"])
async def group_scim(
    group_id: str,
    request: Request,
    context: SCIMContext = Depends(verify_scim_token),
    db: Session = Depends(get_scim_session),
):
    return await SCIMService(db, context).handle(
        "group_" + request.method.lower(), identity=group_id
    )


@router.post("/Bulk")
@router.post("/Users/.search")
@router.post("/Groups/.search")
async def unsupported_scim(
    context: SCIMContext = Depends(verify_scim_token),
    db: Session = Depends(get_scim_session),
):
    return await SCIMService(db, context).handle("unsupported_bulk_or_search")


@router.get("/ServiceProviderConfig")
async def get_service_provider_config():
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": False},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": False, "maxResults": 100},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "Bound SCIM bearer credential",
                "description": "Deployment-configured tenant-bound credential; no OAuth token issuer is provided",
            }
        ],
    }
