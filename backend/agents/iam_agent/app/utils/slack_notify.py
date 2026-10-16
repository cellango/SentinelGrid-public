import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def notify_slack(title: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Send a minimal Slack notification (best-effort). No-op if webhook is not set.
    """
    webhook = settings.SLACK_WEBHOOK_URL
    if not webhook:
        return

    body = {
        "text": title,
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*"}}
        ],
    }
    if context:
        # Render context as code block for readability
        body["blocks"].append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "```" + json.dumps(context, indent=2, default=str) + "```",
                },
            }
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook, json=body)
            if resp.status_code >= 300:
                logger.warning("Slack notify failed: status=%s body=%s", resp.status_code, resp.text[:200])
    except Exception as exc:  # pragma: no cover
        logger.warning("Slack notify error: %s", exc)
