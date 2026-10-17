"""Retired unqualified chat/provider bridge; compatibility signatures only."""

from __future__ import annotations
from typing import Dict, List, Optional
from fastapi import HTTPException


class AIAppOnboardingService:
    def __init__(self):
        pass

    async def process_app_onboarding_request(
        self,
        user_message: str,
        tenant_id: str,
        user_id: str,
        conversation_context: Optional[List[Dict]] = None,
    ) -> Dict:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    async def continue_onboarding_conversation(
        self, user_response: str, onboarding_state: Dict, tenant_id: str, user_id: str
    ) -> Dict:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _extract_app_name(self, message: str) -> str:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    async def _get_app_catalog_info(self, app_name: str) -> Optional[Dict]:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    async def _get_suggested_apps(self) -> List[str]:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    async def _check_existing_app(
        self, app_name: str, tenant_id: str, realm: str
    ) -> Optional[Dict]:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _determine_missing_fields(
        self, onboarding_state: Dict, conversation_context: Optional[List[Dict]]
    ) -> List[str]:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _generate_question_for_fields(self, field: str, app_info: Dict) -> str:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    def _extract_information(self, message: str, required_fields: List[str]) -> Dict:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )

    async def _create_app_from_state(
        self, onboarding_state: Dict, tenant_id: str, realm: str
    ) -> Dict:
        raise HTTPException(
            status_code=501,
            detail="Legacy IAM chat and automatic onboarding are unavailable",
        )
