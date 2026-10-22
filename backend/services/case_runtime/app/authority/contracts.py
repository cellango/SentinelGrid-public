"""Compatibility imports for the shared, versioned action-record contract."""

from sg_core.action_contracts import (
    VERSION,
    LIMIT,
    canonical_uuid,
    strict_json,
    canonical,
    digest,
    Target,
    ProposalInput,
    proposal_payload,
    ApprovalInput,
    ProposalDocument,
    ProposalRecord,
)

__all__ = [
    "VERSION",
    "LIMIT",
    "canonical_uuid",
    "strict_json",
    "canonical",
    "digest",
    "Target",
    "ProposalInput",
    "proposal_payload",
    "ApprovalInput",
    "ProposalDocument",
    "ProposalRecord",
]
