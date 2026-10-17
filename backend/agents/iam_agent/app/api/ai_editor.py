"""Verified administrator policy-draft assistance, separate from policy writers."""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_entitlement_session,
)
from app.models.ai_editor import GenerateRequest, ExplainRequest, UnsupportedRequest
from app.services.ai_policy_service import (
    AIPolicyService,
    require_editor_admin,
    editor_enabled,
)


class EditorRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def no_store(request):
            try:
                response = await handler(request)
            except HTTPException as error:
                response = JSONResponse(
                    {"detail": error.detail}, status_code=error.status_code
                )
            except RequestValidationError:
                response = JSONResponse(
                    {"detail": "Invalid editor request"}, status_code=422
                )
            response.headers["Cache-Control"] = "no-store"
            return response

        return no_store


router = APIRouter(
    prefix="/api/v1/ai/editor", tags=["ai-editor"], route_class=EditorRoute
)


def get_editor_context(
    response: Response, context: RequestContext = Depends(get_current_request_context)
):
    require_editor_admin(context)
    editor_enabled()
    response.headers["Cache-Control"] = "no-store"
    return context


def get_editor_service(
    context=Depends(get_editor_context), db=Depends(get_entitlement_session)
):
    return AIPolicyService(db)


@router.post("/generate")
async def generate(
    request: GenerateRequest,
    context=Depends(get_editor_context),
    service=Depends(get_editor_service),
):
    return await service.assist("generate", request, context)


@router.post("/explain")
async def explain(
    request: ExplainRequest,
    context=Depends(get_editor_context),
    service=Depends(get_editor_service),
):
    return await service.assist("explain", request, context)


@router.post("/suggest")
@router.post("/analyze")
@router.post("/validate-nl")
async def unsupported(request: UnsupportedRequest, context=Depends(get_editor_context)):
    raise HTTPException(status_code=501, detail="AI editor operation is not qualified")
