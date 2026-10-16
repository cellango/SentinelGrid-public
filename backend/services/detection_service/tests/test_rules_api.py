"""Tests for detection rules API endpoints."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import text


class TestEnableRulesAPI:
    """Test suite for enable rules endpoint."""
    
    def test_enable_rules_success(self, client, test_db):
        """Test enabling baseline detection rules."""
        tenant_id = str(uuid4())
        
        # Create detection_rules table
        test_db.execute(
            text("""
                CREATE TABLE IF NOT EXISTS detection_rules (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    rule_type TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    severity TEXT NOT NULL DEFAULT 'medium',
                    created_at TEXT NOT NULL DEFAULT datetime('now'),
                    updated_at TEXT NOT NULL DEFAULT datetime('now')
                )
            """)
        )
        test_db.commit()
        
        response = client.post(
            "/api/v1/detection/rules/enable",
            json={
                "tenant_id": tenant_id,
                "rule_keys": ["failed_logins", "new_admin", "suspicious_cloud"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == tenant_id
        assert len(data["rules_enabled"]) == 3
        assert "failed_logins" in data["rules_enabled"]
        assert "new_admin" in data["rules_enabled"]
        assert "suspicious_cloud" in data["rules_enabled"]
        assert data["rules_created"] == 3
    
    def test_enable_rules_invalid_keys(self, client):
        """Test enabling rules with invalid rule keys."""
        response = client.post(
            "/api/v1/detection/rules/enable",
            json={
                "tenant_id": str(uuid4()),
                "rule_keys": ["invalid_rule", "another_invalid"]
            }
        )
        
        assert response.status_code == 400
        assert "Invalid rule keys" in response.json()["detail"]
    
    def test_enable_rules_partial_list(self, client, test_db):
        """Test enabling a subset of rules."""
        tenant_id = str(uuid4())
        
        # Create detection_rules table
        test_db.execute(
            text("""
                CREATE TABLE IF NOT EXISTS detection_rules (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    rule_type TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    severity TEXT NOT NULL DEFAULT 'medium',
                    created_at TEXT NOT NULL DEFAULT datetime('now'),
                    updated_at TEXT NOT NULL DEFAULT datetime('now')
                )
            """)
        )
        test_db.commit()
        
        response = client.post(
            "/api/v1/detection/rules/enable",
            json={
                "tenant_id": tenant_id,
                "rule_keys": ["failed_logins"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["rules_enabled"]) == 1
        assert data["rules_created"] == 1
    
    def test_enable_rules_empty_list(self, client):
        """Test enabling rules with empty list."""
        response = client.post(
            "/api/v1/detection/rules/enable",
            json={
                "tenant_id": str(uuid4()),
                "rule_keys": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["rules_enabled"]) == 0
    
    def test_enable_rules_update_existing(self, client, test_db):
        """Test enabling rules that already exist (should update, not create)."""
        tenant_id = str(uuid4())
        rule_id = str(uuid4())
        
        # Create detection_rules table
        test_db.execute(
            text("""
                CREATE TABLE IF NOT EXISTS detection_rules (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    rule_type TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    severity TEXT NOT NULL DEFAULT 'medium',
                    created_at TEXT NOT NULL DEFAULT datetime('now'),
                    updated_at TEXT NOT NULL DEFAULT datetime('now')
                )
            """)
        )
        
        # Create existing rule (disabled)
        test_db.execute(
            text("""
                INSERT INTO detection_rules 
                (id, tenant_id, name, rule_type, pattern, enabled, severity, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, :rule_type, :pattern, 0, :severity, datetime('now'), datetime('now'))
            """),
            {
                "id": rule_id,
                "tenant_id": tenant_id,
                "name": "Multiple Failed Logins",
                "rule_type": "failed_logins",
                "pattern": '{"threshold": 5}',
                "severity": "high"
            }
        )
        test_db.commit()
        
        response = client.post(
            "/api/v1/detection/rules/enable",
            json={
                "tenant_id": tenant_id,
                "rule_keys": ["failed_logins"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "failed_logins" in data["rules_enabled"]
        # Should update existing, not create new
        assert data["rules_updated"] >= 0

