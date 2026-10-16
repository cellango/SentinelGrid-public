"""Tests for detection rules."""

import pytest
from datetime import datetime, timedelta
from app.rules.failed_logins import FailedLoginsRule
from app.rules.new_admin import NewAdminRule
from app.rules.suspicious_cloud import SuspiciousCloudRule


class TestFailedLoginsRule:
    """Tests for Failed Logins Rule."""
    
    def test_threshold_not_met(self, test_tenant_id, sample_events):
        """Test that alerts are not generated when threshold is not met."""
        rule_config = {
            "id": "rule-1",
            "name": "Test Rule",
            "severity": "medium",
            "pattern": {
                "threshold": 10,
                "window_minutes": 15,
            },
        }
        
        rule = FailedLoginsRule(rule_config, test_tenant_id)
        
        # Filter only failed login events (6 events)
        failed_events = [e for e in sample_events if "login.failure" in e.get("event_type", "")]
        
        alerts = rule.evaluate(failed_events)
        
        assert len(alerts) == 0  # Threshold is 10, but we only have 6 events
    
    def test_threshold_met(self, test_tenant_id, sample_events):
        """Test that alerts are generated when threshold is met."""
        rule_config = {
            "id": "rule-1",
            "name": "Test Rule",
            "severity": "medium",
            "pattern": {
                "threshold": 5,
                "window_minutes": 15,
            },
        }
        
        rule = FailedLoginsRule(rule_config, test_tenant_id)
        
        # Filter only failed login events (6 events)
        failed_events = [e for e in sample_events if "login.failure" in e.get("event_type", "")]
        
        alerts = rule.evaluate(failed_events)
        
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "medium"
        assert "test@example.com" in alerts[0]["title"]
        assert alerts[0]["metadata"]["failure_count"] == 6
        assert len(alerts[0]["events"]) == 6
    
    def test_multiple_users(self, test_tenant_id):
        """Test that alerts are generated per user."""
        now = datetime.utcnow()
        events = [
            {
                "id": f"event-{i}",
                "@timestamp": (now - timedelta(minutes=i)).isoformat(),
                "event_type": "login.failure",
                "user": {"email": "user1@example.com"},
            }
            for i in range(3)
        ] + [
            {
                "id": f"event-{i}",
                "@timestamp": (now - timedelta(minutes=i)).isoformat(),
                "event_type": "login.failure",
                "user": {"email": "user2@example.com"},
            }
            for i in range(6)
        ]
        
        rule_config = {
            "id": "rule-1",
            "name": "Test Rule",
            "severity": "medium",
            "pattern": {
                "threshold": 5,
                "window_minutes": 15,
            },
        }
        
        rule = FailedLoginsRule(rule_config, test_tenant_id)
        alerts = rule.evaluate(events)
        
        assert len(alerts) == 1  # Only user2 should trigger (6 failures)
        assert "user2@example.com" in alerts[0]["title"]


class TestNewAdminRule:
    """Tests for New Admin Rule."""
    
    def test_admin_user_detected(self, test_tenant_id, sample_events):
        """Test that admin user creation is detected."""
        rule_config = {
            "id": "rule-1",
            "name": "Test Rule",
            "severity": "high",
            "pattern": {
                "admin_keywords": ["admin", "administrator", "root"],
                "check_groups": True,
            },
        }
        
        rule = NewAdminRule(rule_config, test_tenant_id)
        
        # Filter admin creation event
        admin_events = [e for e in sample_events if "user.create" in e.get("event_type", "")]
        
        alerts = rule.evaluate(admin_events)
        
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "high"
        assert "admin_user" in alerts[0]["title"] or "admin@example.com" in alerts[0]["title"]
    
    def test_non_admin_user_not_detected(self, test_tenant_id):
        """Test that regular user creation is not detected."""
        now = datetime.utcnow()
        events = [
            {
                "id": "event-1",
                "@timestamp": now.isoformat(),
                "event_type": "user.create",
                "event_name": "CreateUser",
                "user": {
                    "name": "regular_user",
                    "email": "user@example.com",
                },
            }
        ]
        
        rule_config = {
            "id": "rule-1",
            "name": "Test Rule",
            "severity": "high",
            "pattern": {
                "admin_keywords": ["admin", "administrator", "root"],
                "check_groups": True,
            },
        }
        
        rule = NewAdminRule(rule_config, test_tenant_id)
        alerts = rule.evaluate(events)
        
        assert len(alerts) == 0


class TestSuspiciousCloudRule:
    """Tests for Suspicious Cloud Rule."""
    
    def test_suspicious_action_detected(self, test_tenant_id, sample_events):
        """Test that suspicious cloud actions are detected."""
        rule_config = {
            "id": "rule-1",
            "name": "Test Rule",
            "severity": "high",
            "pattern": {
                "suspicious_actions": [
                    "PutBucketPolicy",
                    "PutBucketAcl",
                    "PutRolePolicy",
                ],
            },
        }
        
        rule = SuspiciousCloudRule(rule_config, test_tenant_id)
        
        # Filter suspicious cloud events
        cloud_events = [e for e in sample_events if "s3" in e.get("event_type", "").lower() or "aws" in e.get("event_type", "").lower()]
        
        alerts = rule.evaluate(cloud_events)
        
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "high"
        assert "PutBucketPolicy" in alerts[0]["title"] or "suspicious" in alerts[0]["title"].lower()
        assert alerts[0]["metadata"]["event_name"] == "PutBucketPolicy"
    
    def test_normal_action_not_detected(self, test_tenant_id):
        """Test that normal cloud actions are not detected."""
        now = datetime.utcnow()
        events = [
            {
                "id": "event-1",
                "@timestamp": now.isoformat(),
                "event_type": "aws.s3.get",
                "event_name": "GetObject",
                "user": {"email": "user@example.com"},
            }
        ]
        
        rule_config = {
            "id": "rule-1",
            "name": "Test Rule",
            "severity": "high",
            "pattern": {
                "suspicious_actions": ["PutBucketPolicy"],
            },
        }
        
        rule = SuspiciousCloudRule(rule_config, test_tenant_id)
        alerts = rule.evaluate(events)
        
        assert len(alerts) == 0

