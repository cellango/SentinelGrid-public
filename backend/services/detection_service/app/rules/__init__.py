"""Detection rule modules."""

from .base import BaseRule
from .failed_logins import FailedLoginsRule
from .new_admin import NewAdminRule
from .suspicious_cloud import SuspiciousCloudRule

RULE_MAP = {
    "failed_logins": FailedLoginsRule,
    "new_admin": NewAdminRule,
    "suspicious_cloud": SuspiciousCloudRule,
}

__all__ = ["BaseRule", "FailedLoginsRule", "NewAdminRule", "SuspiciousCloudRule", "RULE_MAP"]

