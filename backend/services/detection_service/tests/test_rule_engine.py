"""Tests for rule engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.engine.rule_engine import RuleEngine
from app.models.rule import DetectionRule
from uuid import UUID


@pytest.mark.asyncio
async def test_evaluate_rule_with_events(db_session, sample_failed_logins_rule, sample_events, test_tenant_id):
    """Test rule evaluation with provided events."""
    engine = RuleEngine(db_session)
    
    # Filter relevant events
    failed_events = [e for e in sample_events if "login.failure" in e.get("event_type", "")]
    
    alerts = await engine.evaluate_rule(sample_failed_logins_rule, events=failed_events)
    
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "medium"
    assert alerts[0]["metadata"]["rule_name"] == "Test Failed Logins Rule"


@pytest.mark.asyncio
async def test_evaluate_disabled_rule(db_session, sample_failed_logins_rule, sample_events, test_tenant_id):
    """Test that disabled rules are not evaluated."""
    sample_failed_logins_rule.enabled = False
    db_session.commit()
    
    engine = RuleEngine(db_session)
    
    failed_events = [e for e in sample_events if "login.failure" in e.get("event_type", "")]
    alerts = await engine.evaluate_rule(sample_failed_logins_rule, events=failed_events)
    
    assert len(alerts) == 0


@pytest.mark.asyncio
async def test_evaluate_all_rules(db_session, sample_failed_logins_rule, sample_new_admin_rule, sample_events, test_tenant_id):
    """Test evaluation of all enabled rules."""
    engine = RuleEngine(db_session)
    
    # Mock the fetch_recent_events method to return our sample events
    with patch.object(engine, 'evaluate_rule') as mock_evaluate:
        # Configure mock to return different alerts for different rules
        def side_effect(rule, events=None):
            if rule.rule_type == "failed_logins":
                return [{"id": "alert-1", "rule_type": "failed_logins"}]
            elif rule.rule_type == "new_admin":
                return [{"id": "alert-2", "rule_type": "new_admin"}]
            return []
        
        mock_evaluate.side_effect = side_effect
        
        results = await engine.evaluate_all_rules(test_tenant_id)
        
        assert results["total_rules"] == 2
        assert results["alerts_generated"] == 2
        assert len(results["rule_results"]) == 2


@pytest.mark.asyncio
async def test_evaluate_unknown_rule_type(db_session, test_tenant_id):
    """Test that unknown rule types are handled gracefully."""
    from uuid import uuid4
    
    rule = DetectionRule(
        id=uuid4(),
        tenant_id=UUID(test_tenant_id),
        name="Unknown Rule",
        rule_type="unknown_type",
        pattern={},
        enabled=True,
    )
    db_session.add(rule)
    db_session.commit()
    
    engine = RuleEngine(db_session)
    alerts = await engine.evaluate_rule(rule)
    
    assert len(alerts) == 0

