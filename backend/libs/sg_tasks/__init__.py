"""SentinelGrid Async Task Library

Celery-based task processing infrastructure for playbook execution,
bulk operations, report generation, and agent task orchestration.
"""

__version__ = "0.1.0"

from sg_tasks.celery_app import celery_app  # noqa: F401
