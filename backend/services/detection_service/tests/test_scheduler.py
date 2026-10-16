"""Tests for scheduler functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from app.services.scheduler import (
    get_scheduler,
    start_scheduler,
    stop_scheduler,
    evaluate_all_rules_job,
)


@pytest.mark.asyncio
async def test_evaluate_all_rules_job(test_tenant_id):
    """Test the rule evaluation job."""
    with patch("app.services.scheduler.RuleEngine") as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Mock evaluation results
        mock_results = {
            "total_rules": 2,
            "alerts_generated": 3,
            "rule_results": [
                {
                    "rule_id": "rule-1",
                    "alerts": [
                        {"id": "alert-1", "tenant_id": test_tenant_id},
                        {"id": "alert-2", "tenant_id": test_tenant_id},
                    ],
                },
                {
                    "rule_id": "rule-2",
                    "alerts": [
                        {"id": "alert-3", "tenant_id": test_tenant_id},
                    ],
                },
            ],
        }
        mock_engine.evaluate_all_rules = AsyncMock(return_value=mock_results)
        
        # Mock alert creation
        with patch("app.services.scheduler.create_alerts") as mock_create:
            mock_create.return_value = {"created": 3, "failed": 0}
            
            result = await evaluate_all_rules_job(test_tenant_id)
            
            assert result is not None
            assert result["total_rules"] == 2
            assert result["alerts_generated"] == 3
            mock_create.assert_called_once()


def test_start_stop_scheduler():
    """Test starting and stopping the scheduler."""
    scheduler = get_scheduler()
    
    # Ensure scheduler is stopped
    if scheduler.running:
        stop_scheduler()
    
    assert not scheduler.running
    
    # Start scheduler
    start_scheduler()
    
    assert scheduler.running
    assert len(scheduler.get_jobs()) > 0
    
    # Stop scheduler
    stop_scheduler()
    
    assert not scheduler.running

