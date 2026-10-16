"""Compatibility wrapper over the shared SOC response-pack matcher."""

from sg_agent_runtime.response_pack_matcher import (
    MatchedResponsePack,
    ResponsePackContext,
    ResponsePackDefinition,
    RESPONSE_PACKS,
    build_incident_context,
    match_pack_playbooks,
    match_response_packs_for_incident,
    normalize_token,
    playbook_rank,
    playbook_search_text,
    score_pack,
    unique_strings,
)

__all__ = [
    "MatchedResponsePack",
    "ResponsePackContext",
    "ResponsePackDefinition",
    "RESPONSE_PACKS",
    "build_incident_context",
    "match_pack_playbooks",
    "match_response_packs_for_incident",
    "normalize_token",
    "playbook_rank",
    "playbook_search_text",
    "score_pack",
    "unique_strings",
]
