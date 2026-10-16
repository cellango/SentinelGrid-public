"""SOAR wrapper around the shared SOC response planner."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sg_agent_runtime.soc_models import SOCRecommendationOutput
from sg_agent_runtime.soc_response_planner import SOCResponsePlanner


class PlaybookRecommender:
    """Service wrapper that preserves the existing SOAR async API surface."""

    def __init__(self) -> None:
        self.planner = SOCResponsePlanner()

    async def recommend_playbooks(
        self,
        ticket_data: dict[str, Any],
        available_playbooks: list[dict[str, Any]],
        tenant_id: UUID | str,
    ) -> list[dict[str, Any]]:
        """Legacy wrapper returning ranked playbooks for older SOAR callers."""
        plan = await self.recommend_response_plan(ticket_data, available_playbooks, tenant_id)
        return [
            {
                "playbook_id": recommendation.playbook_id,
                "playbook_key": recommendation.playbook_key,
                "playbook_name": recommendation.playbook_name,
                "score": recommendation.confidence,
                "reasons": recommendation.rationale,
                "response_pack_id": plan.response_pack_id,
                "response_pack_label": plan.response_pack_label,
            }
            for recommendation in plan.recommended_playbooks
        ]

    async def recommend_response_plan(
        self,
        ticket_data: dict[str, Any],
        available_playbooks: list[dict[str, Any]],
        tenant_id: UUID | str,
    ) -> SOCRecommendationOutput:
        del tenant_id  # reserved for later tenant-aware planner refinement
        return self.planner.recommend_response_plan(ticket_data, available_playbooks)
