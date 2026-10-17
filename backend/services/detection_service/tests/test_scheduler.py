"""No lifecycle call can fabricate started/completed effects from a raw UUID."""

import asyncio
from datetime import datetime, timezone
import pytest
from app.services import scheduler


@pytest.mark.parametrize(
    "action", ["start", "stop", "one_time", "job_global", "job_tenant"]
)
def test_scheduler_lifecycle_requires_owned_contract(action):
    with pytest.raises(RuntimeError, match="Owned detection scheduler workload"):
        if action == "start":
            scheduler.start_scheduler()
        elif action == "stop":
            scheduler.stop_scheduler()
        elif action == "one_time":
            scheduler.add_one_time_job(lambda: None, datetime.now(timezone.utc))
        else:
            asyncio.run(
                scheduler.evaluate_all_rules_job(
                    None
                    if action == "job_global"
                    else "11111111-1111-4111-8111-111111111111"
                )
            )
