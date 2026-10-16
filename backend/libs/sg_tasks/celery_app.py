"""Celery application configuration for SentinelGrid async task processing.

Provides a pre-configured Celery instance with dedicated queues for
playbooks, reports, bulk operations, and agent tasks.
"""

import os
import logging

from celery import Celery
from kombu import Exchange, Queue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Broker / result backend
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

# ---------------------------------------------------------------------------
# Celery application
# ---------------------------------------------------------------------------
celery_app = Celery(
    "sg_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True

# ---------------------------------------------------------------------------
# Reliability
# ---------------------------------------------------------------------------
celery_app.conf.task_acks_late = True
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.task_track_started = True
celery_app.conf.result_expires = 60 * 60 * 24  # 24 hours

# ---------------------------------------------------------------------------
# Queues
# ---------------------------------------------------------------------------
default_exchange = Exchange("default", type="direct")
agents_exchange = Exchange("agents", type="direct")
playbooks_exchange = Exchange("playbooks", type="direct")
reports_exchange = Exchange("reports", type="direct")
bulk_ops_exchange = Exchange("bulk_ops", type="direct")

celery_app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("agents", agents_exchange, routing_key="agents"),
    Queue("playbooks", playbooks_exchange, routing_key="playbooks"),
    Queue("reports", reports_exchange, routing_key="reports"),
    Queue("bulk_ops", bulk_ops_exchange, routing_key="bulk_ops"),
)
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

# ---------------------------------------------------------------------------
# Task routing
# ---------------------------------------------------------------------------
celery_app.conf.task_routes = {
    "sg_tasks.tasks.run_playbook_*": {"queue": "playbooks"},
    "sg_tasks.tasks.generate_report*": {"queue": "reports"},
    "sg_tasks.tasks.bulk_*": {"queue": "bulk_ops"},
    "sg_tasks.tasks.agent_*": {"queue": "agents"},
}

# ---------------------------------------------------------------------------
# Auto-discover tasks
# ---------------------------------------------------------------------------
celery_app.autodiscover_tasks(["sg_tasks"])

logger.info(
    "Celery app configured: broker=%s backend=%s",
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
)
