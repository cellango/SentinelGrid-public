"""NIST SP 800-61 incident workflow integration for SOAR agent."""

import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NISTPhase(str, Enum):
    """NIST SP 800-61 incident response phases."""
    PREPARATION = "preparation"
    DETECTION_AND_ANALYSIS = "detection_and_analysis"
    CONTAINMENT = "containment"
    ERADICATION = "eradication"
    RECOVERY = "recovery"
    POST_INCIDENT = "post_incident"


class NISTStatus(str, Enum):
    """NIST-aligned incident status."""
    # Detection & Analysis Phase
    NEW = "new"  # Newly detected
    TRIAGED = "triaged"  # Initial analysis complete
    INVESTIGATING = "investigating"  # Under investigation
    
    # Containment Phase
    CONTAINED = "contained"  # Threat contained
    ISOLATED = "isolated"  # System isolated
    
    # Eradication Phase
    ERADICATING = "eradicating"  # Removing threat
    ERADICATED = "eradicated"  # Threat removed
    
    # Recovery Phase
    RECOVERING = "recovering"  # System recovery in progress
    RECOVERED = "recovered"  # System recovered
    
    # Post-Incident Phase
    LESSONS_LEARNED = "lessons_learned"  # Post-incident review
    CLOSED = "closed"  # Incident closed


class NISTWorkflowEngine:
    """NIST SP 800-61 compliant workflow engine for SOAR."""
    
    # Valid status transitions (from -> to)
    VALID_TRANSITIONS: Dict[NISTStatus, List[NISTStatus]] = {
        # Detection & Analysis Phase
        NISTStatus.NEW: [NISTStatus.TRIAGED, NISTStatus.INVESTIGATING, NISTStatus.CLOSED],
        NISTStatus.TRIAGED: [NISTStatus.INVESTIGATING, NISTStatus.CONTAINED, NISTStatus.CLOSED],
        NISTStatus.INVESTIGATING: [NISTStatus.CONTAINED, NISTStatus.ISOLATED, NISTStatus.CLOSED],
        
        # Containment Phase
        NISTStatus.CONTAINED: [NISTStatus.ISOLATED, NISTStatus.ERADICATING, NISTStatus.CLOSED],
        NISTStatus.ISOLATED: [NISTStatus.ERADICATING, NISTStatus.CLOSED],
        
        # Eradication Phase
        NISTStatus.ERADICATING: [NISTStatus.ERADICATED, NISTStatus.CLOSED],
        NISTStatus.ERADICATED: [NISTStatus.RECOVERING, NISTStatus.CLOSED],
        
        # Recovery Phase
        NISTStatus.RECOVERING: [NISTStatus.RECOVERED, NISTStatus.CLOSED],
        NISTStatus.RECOVERED: [NISTStatus.LESSONS_LEARNED, NISTStatus.CLOSED],
        
        # Post-Incident Phase
        NISTStatus.LESSONS_LEARNED: [NISTStatus.CLOSED],
        NISTStatus.CLOSED: [],  # Terminal state
    }
    
    # Status to Phase mapping
    STATUS_TO_PHASE: Dict[NISTStatus, NISTPhase] = {
        NISTStatus.NEW: NISTPhase.DETECTION_AND_ANALYSIS,
        NISTStatus.TRIAGED: NISTPhase.DETECTION_AND_ANALYSIS,
        NISTStatus.INVESTIGATING: NISTPhase.DETECTION_AND_ANALYSIS,
        NISTStatus.CONTAINED: NISTPhase.CONTAINMENT,
        NISTStatus.ISOLATED: NISTPhase.CONTAINMENT,
        NISTStatus.ERADICATING: NISTPhase.ERADICATION,
        NISTStatus.ERADICATED: NISTPhase.ERADICATION,
        NISTStatus.RECOVERING: NISTPhase.RECOVERY,
        NISTStatus.RECOVERED: NISTPhase.RECOVERY,
        NISTStatus.LESSONS_LEARNED: NISTPhase.POST_INCIDENT,
        NISTStatus.CLOSED: NISTPhase.POST_INCIDENT,
    }
    
    @classmethod
    def get_initial_status(cls) -> NISTStatus:
        """Get initial status for new incidents."""
        return NISTStatus.NEW
    
    @classmethod
    def get_initial_phase(cls) -> NISTPhase:
        """Get initial phase for new incidents."""
        return NISTPhase.DETECTION_AND_ANALYSIS
    
    @classmethod
    def get_phase_for_status(cls, status: Union[str, NISTStatus]) -> NISTPhase:
        """Get NIST phase for a given status."""
        try:
            nist_status = NISTStatus(status) if isinstance(status, str) else status
            return cls.STATUS_TO_PHASE.get(nist_status, NISTPhase.DETECTION_AND_ANALYSIS)
        except ValueError:
            return NISTPhase.DETECTION_AND_ANALYSIS
    
    @classmethod
    def validate_transition(
        cls,
        current_status: Union[str, NISTStatus],
        new_status: Union[str, NISTStatus]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if a status transition is allowed.
        
        Args:
            current_status: Current incident status
            new_status: Desired new status
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            current = NISTStatus(current_status) if isinstance(current_status, str) else current_status
            new = NISTStatus(new_status) if isinstance(new_status, str) else new_status
        except ValueError:
            return False, f"Invalid status: {current_status} or {new_status}"
        
        if current == new:
            return True, None
        
        allowed_transitions = cls.VALID_TRANSITIONS.get(current, [])
        if new not in allowed_transitions:
            return False, f"Invalid transition from {current.value} to {new.value}"
        
        return True, None
    
    @classmethod
    def get_allowed_transitions(cls, current_status: Union[str, NISTStatus]) -> List[str]:
        """Get list of allowed next statuses."""
        try:
            current = NISTStatus(current_status) if isinstance(current_status, str) else current_status
            return [s.value for s in cls.VALID_TRANSITIONS.get(current, [])]
        except ValueError:
            return []
    
    @classmethod
    def get_phase_requirements(cls, phase: Union[str, NISTPhase]) -> Dict[str, Any]:
        """Get requirements and activities for a NIST phase."""
        try:
            nist_phase = NISTPhase(phase) if isinstance(phase, str) else phase
        except ValueError:
            return {}
        
        requirements = {
            NISTPhase.PREPARATION: {
                "description": "Preparation phase - Establish incident response capability",
                "activities": [
                    "Incident response plan",
                    "Incident response team",
                    "Tools and resources",
                    "Training"
                ],
                "nist_controls": ["IR-1", "IR-2", "IR-3"]
            },
            NISTPhase.DETECTION_AND_ANALYSIS: {
                "description": "Detection and Analysis - Identify and analyze security incidents",
                "activities": [
                    "Event detection",
                    "Initial analysis",
                    "Incident classification",
                    "Incident documentation"
                ],
                "nist_controls": ["IR-4", "IR-5", "IR-6"]
            },
            NISTPhase.CONTAINMENT: {
                "description": "Containment - Limit the damage from the incident",
                "activities": [
                    "Short-term containment",
                    "Long-term containment",
                    "System isolation",
                    "Evidence preservation"
                ],
                "nist_controls": ["IR-4", "IR-7"]
            },
            NISTPhase.ERADICATION: {
                "description": "Eradication - Remove the threat from the environment",
                "activities": [
                    "Threat removal",
                    "Malware removal",
                    "Vulnerability patching",
                    "System hardening"
                ],
                "nist_controls": ["IR-4", "SI-2", "SI-3"]
            },
            NISTPhase.RECOVERY: {
                "description": "Recovery - Restore systems to normal operation",
                "activities": [
                    "System restoration",
                    "Service validation",
                    "Monitoring",
                    "Documentation"
                ],
                "nist_controls": ["IR-4", "CP-10"]
            },
            NISTPhase.POST_INCIDENT: {
                "description": "Post-Incident Activity - Learn from the incident",
                "activities": [
                    "Lessons learned",
                    "Incident report",
                    "Process improvement",
                    "Documentation"
                ],
                "nist_controls": ["IR-4", "IR-8"]
            }
        }
        
        return requirements.get(nist_phase, {})

