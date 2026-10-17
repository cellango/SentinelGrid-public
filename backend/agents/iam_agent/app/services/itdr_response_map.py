"""Versioned proposal catalog; mappings are not detection facts or execution authority."""

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType


class ThreatType(str, Enum):
    """Identity threat categories detected by anomaly/risk services."""

    IMPOSSIBLE_TRAVEL = "impossible_travel"
    FAILED_LOGIN_SPIKE = "failed_login_spike"
    NEW_DEVICE_HIGH_RISK = "new_device_high_risk"
    STALE_PRIVILEGED_ACCESS = "stale_privileged_access"
    RISK_SCORE_HIGH = "risk_score_high"
    RISK_SCORE_CRITICAL = "risk_score_critical"
    CREDENTIAL_STUFFING = "credential_stuffing"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ACCOUNT_TAKEOVER = "account_takeover"
    MFA_FATIGUE = "mfa_fatigue"


class ResponseAction(str, Enum):
    """Actions that can be taken in response to identity threats."""

    LOG_ALERT = "log_alert"
    NOTIFY_USER = "notify_user"
    NOTIFY_SOC = "notify_soc"
    REQUIRE_REAUTH = "require_reauth"
    REQUIRE_STEP_UP = "require_step_up"
    KILL_SESSIONS = "kill_sessions"
    LOCK_ACCOUNT = "lock_account"
    CREATE_INCIDENT = "create_incident"
    RESTRICT_ACCESS = "restrict_access"
    BLOCK_IP = "block_ip"
    FLAG_FOR_REVIEW = "flag_for_review"


class ResponseSeverity(str, Enum):
    """Severity of the automated response."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ThreatResponse:
    threat_type: ThreatType
    severity: ResponseSeverity
    actions: tuple[ResponseAction, ...]
    soar_workflow_id: str | None = None
    requires_human_approval: bool = False


THREAT_RESPONSE_MAP = MappingProxyType(
    {
        ThreatType.IMPOSSIBLE_TRAVEL: ThreatResponse(
            ThreatType.IMPOSSIBLE_TRAVEL,
            ResponseSeverity.HIGH,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.KILL_SESSIONS,
                ResponseAction.REQUIRE_REAUTH,
                ResponseAction.REQUIRE_STEP_UP,
                ResponseAction.NOTIFY_USER,
                ResponseAction.CREATE_INCIDENT,
            ),
            "itdr_impossible_travel",
            False,
        ),
        ThreatType.FAILED_LOGIN_SPIKE: ThreatResponse(
            ThreatType.FAILED_LOGIN_SPIKE,
            ResponseSeverity.HIGH,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.LOCK_ACCOUNT,
                ResponseAction.NOTIFY_USER,
                ResponseAction.NOTIFY_SOC,
                ResponseAction.CREATE_INCIDENT,
            ),
            "itdr_brute_force",
            False,
        ),
        ThreatType.NEW_DEVICE_HIGH_RISK: ThreatResponse(
            ThreatType.NEW_DEVICE_HIGH_RISK,
            ResponseSeverity.MEDIUM,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.REQUIRE_STEP_UP,
                ResponseAction.NOTIFY_USER,
            ),
            None,
            False,
        ),
        ThreatType.STALE_PRIVILEGED_ACCESS: ThreatResponse(
            ThreatType.STALE_PRIVILEGED_ACCESS,
            ResponseSeverity.MEDIUM,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.FLAG_FOR_REVIEW,
                ResponseAction.NOTIFY_SOC,
            ),
            None,
            True,
        ),
        ThreatType.RISK_SCORE_HIGH: ThreatResponse(
            ThreatType.RISK_SCORE_HIGH,
            ResponseSeverity.MEDIUM,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.REQUIRE_STEP_UP,
                ResponseAction.RESTRICT_ACCESS,
            ),
            None,
            False,
        ),
        ThreatType.RISK_SCORE_CRITICAL: ThreatResponse(
            ThreatType.RISK_SCORE_CRITICAL,
            ResponseSeverity.CRITICAL,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.KILL_SESSIONS,
                ResponseAction.LOCK_ACCOUNT,
                ResponseAction.CREATE_INCIDENT,
                ResponseAction.NOTIFY_SOC,
                ResponseAction.NOTIFY_USER,
            ),
            "itdr_critical_risk",
            False,
        ),
        ThreatType.CREDENTIAL_STUFFING: ThreatResponse(
            ThreatType.CREDENTIAL_STUFFING,
            ResponseSeverity.HIGH,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.BLOCK_IP,
                ResponseAction.NOTIFY_SOC,
                ResponseAction.CREATE_INCIDENT,
            ),
            "itdr_credential_stuffing",
            False,
        ),
        ThreatType.PRIVILEGE_ESCALATION: ThreatResponse(
            ThreatType.PRIVILEGE_ESCALATION,
            ResponseSeverity.CRITICAL,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.KILL_SESSIONS,
                ResponseAction.FLAG_FOR_REVIEW,
                ResponseAction.CREATE_INCIDENT,
                ResponseAction.NOTIFY_SOC,
            ),
            "itdr_privilege_escalation",
            True,
        ),
        ThreatType.ACCOUNT_TAKEOVER: ThreatResponse(
            ThreatType.ACCOUNT_TAKEOVER,
            ResponseSeverity.CRITICAL,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.LOCK_ACCOUNT,
                ResponseAction.KILL_SESSIONS,
                ResponseAction.NOTIFY_USER,
                ResponseAction.NOTIFY_SOC,
                ResponseAction.CREATE_INCIDENT,
            ),
            "itdr_account_takeover",
            False,
        ),
        ThreatType.MFA_FATIGUE: ThreatResponse(
            ThreatType.MFA_FATIGUE,
            ResponseSeverity.HIGH,
            (
                ResponseAction.LOG_ALERT,
                ResponseAction.LOCK_ACCOUNT,
                ResponseAction.NOTIFY_USER,
                ResponseAction.NOTIFY_SOC,
                ResponseAction.CREATE_INCIDENT,
            ),
            "itdr_mfa_fatigue",
            False,
        ),
    }
)

_ADVISORY = frozenset(
    {
        ResponseAction.LOG_ALERT,
        ResponseAction.NOTIFY_SOC,
        ResponseAction.FLAG_FOR_REVIEW,
    }
)


def get_response_for_threat(threat_type):
    return THREAT_RESPONSE_MAP[threat_type]


def get_advisory_actions(response):
    return tuple(a for a in response.actions if a in _ADVISORY)


def get_enforcement_actions(response):
    return tuple(a for a in response.actions if a not in _ADVISORY)
