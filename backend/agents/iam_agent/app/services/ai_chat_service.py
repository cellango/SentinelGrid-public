"""Retired unqualified chat/provider bridge; compatibility signatures only."""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.keycloak_client import KeycloakClient
    from app.services.model_provider import ModelProvider
from fastapi import HTTPException


class IAMChatService:
    def __init__(
        self,
        keycloak_client: KeycloakClient,
        model_provider: Optional[ModelProvider] = None,
    ):
        pass

    async def chat(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _classify_intent(self, query: str) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _gather_iam_data(
        self, intent: Dict[str, Any], tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _build_prompt(
        self,
        query: str,
        intent: Dict[str, Any],
        iam_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _query_llm(self, prompt: str) -> str:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _parse_response(
        self, response: str, intent: Dict[str, Any], iam_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _get_sources(
        self, intent: Dict[str, Any], iam_data: Dict[str, Any]
    ) -> List[str]:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )
