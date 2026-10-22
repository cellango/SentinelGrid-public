"""Application action records for case_runtime; no workflow/provider execution."""

from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import FastAPI, Request, Depends, HTTPException
from sqlalchemy import create_engine
from pydantic import ValidationError
from sg_core.action_identity import require_actor
from sg_core.http_ingress import GatewayIngressMiddleware, IngressPolicy
from sg_core.http_rate_limit import create_budget_store, PeerBudgetMiddleware
from app.config import Settings
from app.authority.contracts import (
    ProposalInput,
    ApprovalInput,
    strict_json,
    canonical_uuid,
    canonical,
)
from app.authority.store import ActionAuthority


def create_app(config: Settings | None = None):
    config = config if config is not None else Settings()

    def admission(request: Request):
        if (request.method, request.url.path) in {
            ("GET", "/"),
            ("GET", "/health"),
            ("GET", "/ready"),
        }:
            return
        actor = require_actor(request)
        if app.state.request_budget_store is not None:
            app.state.request_budget_store.check_identity(actor)
        return actor

    engine = None
    if config.ACTION_AUTHORITY_ENABLED:
        engine = create_engine(
            config.ACTION_AUTHORITY_DATABASE_URL,
            pool_size=2,
            max_overflow=0,
            pool_timeout=2,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 2,
                "options": "-c statement_timeout=3000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000",
            },
        )

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    app = FastAPI(
        title="SentinelGrid case_runtime action records",
        dependencies=[Depends(admission)],
        lifespan=lifespan,
    )
    app.state.request_budget_store = create_budget_store(config.ACTION_RATE_POLICY)
    app.add_middleware(PeerBudgetMiddleware, store=app.state.request_budget_store)
    app.state.iam_verification_settings = config.verification_settings()
    app.state.user_principal_settings = config.user_settings()
    app.state.action_authority = (
        ActionAuthority(
            engine, policy_version=config.ACTION_POLICY_VERSION, enabled=True
        )
        if engine is not None
        else None
    )
    app.add_middleware(
        GatewayIngressMiddleware,
        policy=IngressPolicy(
            allowed_origins=(), max_body_bytes=32768, max_concurrent_requests=16
        ),
    )

    def authority():
        if not config.ACTION_AUTHORITY_ENABLED:
            raise HTTPException(503, "Action authority is unavailable")
        return app.state.action_authority

    async def body(request, model):
        if request.scope.get("query_string"):
            raise HTTPException(
                400, "Action authority does not accept query identity or options"
            )
        try:
            value = strict_json(await request.body())
            canonical(value)
            return model.model_validate(value)
        except (ValueError, TypeError, UnicodeError, ValidationError, RecursionError):
            raise HTTPException(422, "Invalid action request") from None

    @app.get("/")
    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "case_runtime",
            "provider_execution": "unavailable",
            "workflow_execution": "unavailable",
        }

    @app.get("/ready")
    def ready():
        raise HTTPException(503, "Case workflow/provider execution is not qualified")

    @app.post("/api/v1/cases/{case_id}/action-proposals", status_code=201)
    async def submit(case_id: UUID, request: Request):
        parsed = await body(request, ProposalInput)
        keys = request.headers.getlist("idempotency-key")
        try:
            if len(keys) != 1:
                raise ValueError()
            canonical_uuid(keys[0])
        except (ValueError, TypeError):
            raise HTTPException(400, "One UUID Idempotency-Key required") from None
        from anyio import to_thread

        return await to_thread.run_sync(
            authority().submit, request, str(case_id), parsed, keys[0]
        )

    @app.get("/api/v1/cases/{case_id}/action-proposals/{proposal_id}")
    def inspect(case_id: UUID, proposal_id: UUID, request: Request):
        if request.scope.get("query_string"):
            raise HTTPException(400, "Action query options unsupported")
        return authority().inspect(request, str(proposal_id), case_id=str(case_id))

    @app.post(
        "/api/v1/cases/{case_id}/action-proposals/{proposal_id}/approvals",
        status_code=201,
    )
    async def decide(case_id: UUID, proposal_id: UUID, request: Request):
        parsed = await body(request, ApprovalInput)
        from functools import partial
        from anyio import to_thread

        return await to_thread.run_sync(
            partial(
                authority().decide,
                request,
                str(proposal_id),
                parsed,
                case_id=str(case_id),
            )
        )

    return app


app = create_app()
