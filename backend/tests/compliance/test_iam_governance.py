"""
Tests for IAM Governance features (Access Reviews, JML, MFA)
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import text


class TestAccessReviewCampaigns:
    """Test access review campaign functionality."""
    
    def test_create_access_review_campaign(self, db_session, tenant_a, test_user_a):
        """Test creating an access review campaign."""
        campaign_id = uuid4()
        
        db_session.execute(
            text("""
                INSERT INTO access_review_campaigns (
                    id, tenant_id, realm_name, name, campaign_type,
                    scope, status, start_date, end_date, created_by
                )
                VALUES (
                    :id, :tenant_id, :realm_name, :name, :campaign_type,
                    :scope, :status, :start_date, :end_date, :created_by
                )
            """),
            {
                "id": str(campaign_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "name": "Q4 2025 Admin Review",
                "campaign_type": "admin_review",
                "scope": '{"roles": ["TENANT_ADMIN", "SOC_MANAGER"]}',
                "status": "draft",
                "start_date": datetime.utcnow(),
                "end_date": datetime.utcnow() + timedelta(days=14),
                "created_by": test_user_a["id"]
            }
        )
        
        db_session.commit()
        
        # Verify campaign created
        result = db_session.execute(
            text("SELECT name, campaign_type, status FROM access_review_campaigns WHERE id = :id"),
            {"id": str(campaign_id)}
        )
        
        campaign = result.fetchone()
        assert campaign is not None
        assert campaign[0] == "Q4 2025 Admin Review"
        assert campaign[1] == "admin_review"
        assert campaign[2] == "draft"
    
    def test_create_review_items(self, db_session, tenant_a):
        """Test creating review items for a campaign."""
        campaign_id = uuid4()
        item_id = uuid4()
        
        # Create campaign
        db_session.execute(
            text("""
                INSERT INTO access_review_campaigns (id, tenant_id, realm_name, name, campaign_type, created_by)
                VALUES (:id, :tenant_id, :realm_name, 'Test Campaign', 'admin_review', 'admin')
            """),
            {"id": str(campaign_id), "tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        # Create review item
        db_session.execute(
            text("""
                INSERT INTO access_review_items (
                    id, campaign_id, tenant_id, realm_name,
                    reviewer_user_id, reviewer_email,
                    subject_user_id, subject_email,
                    access_type, access_name, decision
                )
                VALUES (
                    :id, :campaign_id, :tenant_id, :realm_name,
                    :reviewer_user_id, :reviewer_email,
                    :subject_user_id, :subject_email,
                    :access_type, :access_name, :decision
                )
            """),
            {
                "id": str(item_id),
                "campaign_id": str(campaign_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "reviewer_user_id": "manager-123",
                "reviewer_email": "manager@acme.com",
                "subject_user_id": "employee-456",
                "subject_email": "employee@acme.com",
                "access_type": "role",
                "access_name": "TENANT_ADMIN",
                "decision": "pending"
            }
        )
        
        db_session.commit()
        
        # Verify item created
        result = db_session.execute(
            text("SELECT access_name, decision FROM access_review_items WHERE id = :id"),
            {"id": str(item_id)}
        )
        
        item = result.fetchone()
        assert item is not None
        assert item[0] == "TENANT_ADMIN"
        assert item[1] == "pending"
    
    def test_record_review_decision(self, db_session, tenant_a):
        """Test recording a review decision with audit trail."""
        campaign_id = uuid4()
        item_id = uuid4()
        decision_id = uuid4()
        
        # Create campaign and item
        db_session.execute(
            text("""
                INSERT INTO access_review_campaigns (id, tenant_id, realm_name, name, campaign_type, created_by)
                VALUES (:id, :tenant_id, :realm_name, 'Test', 'admin_review', 'admin')
            """),
            {"id": str(campaign_id), "tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        db_session.execute(
            text("""
                INSERT INTO access_review_items (id, campaign_id, tenant_id, realm_name, reviewer_user_id, subject_user_id, access_type, access_name)
                VALUES (:id, :campaign_id, :tenant_id, :realm_name, 'reviewer', 'subject', 'role', 'ADMIN')
            """),
            {
                "id": str(item_id),
                "campaign_id": str(campaign_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"]
            }
        )
        
        # Record decision
        db_session.execute(
            text("""
                INSERT INTO access_review_decisions (
                    id, review_item_id, tenant_id, realm_name,
                    reviewer_user_id, reviewer_email, decision, justification
                )
                VALUES (:id, :item_id, :tenant_id, :realm_name, :reviewer, :email, :decision, :justification)
            """),
            {
                "id": str(decision_id),
                "item_id": str(item_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "reviewer": "manager-123",
                "email": "manager@acme.com",
                "decision": "approved",
                "justification": "User requires admin access for their role"
            }
        )
        
        db_session.commit()
        
        # Verify decision recorded
        result = db_session.execute(
            text("SELECT decision, justification FROM access_review_decisions WHERE id = :id"),
            {"id": str(decision_id)}
        )
        
        decision = result.fetchone()
        assert decision is not None
        assert decision[0] == "approved"
        assert "admin access" in decision[1]


class TestJMLWorkflows:
    """Test Joiner/Mover/Leaver workflows."""
    
    def test_create_joiner_workflow(self, db_session, tenant_a, test_user_a):
        """Test creating a joiner (onboarding) workflow."""
        workflow_id = uuid4()
        
        db_session.execute(
            text("""
                INSERT INTO jml_workflows (
                    id, tenant_id, realm_name, workflow_type,
                    target_email, target_name, status, initiated_by
                )
                VALUES (:id, :tenant_id, :realm_name, :workflow_type, :email, :name, :status, :initiated_by)
            """),
            {
                "id": str(workflow_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "workflow_type": "joiner",
                "email": "newuser@acme.com",
                "name": "New User",
                "status": "pending",
                "initiated_by": test_user_a["id"]
            }
        )
        
        db_session.commit()
        
        # Verify workflow created
        result = db_session.execute(
            text("SELECT workflow_type, target_email, status FROM jml_workflows WHERE id = :id"),
            {"id": str(workflow_id)}
        )
        
        workflow = result.fetchone()
        assert workflow is not None
        assert workflow[0] == "joiner"
        assert workflow[1] == "newuser@acme.com"
        assert workflow[2] == "pending"
    
    def test_create_leaver_workflow(self, db_session, tenant_a, test_user_a):
        """Test creating a leaver (offboarding) workflow."""
        workflow_id = uuid4()
        
        db_session.execute(
            text("""
                INSERT INTO jml_workflows (
                    id, tenant_id, realm_name, workflow_type,
                    subject_user_id, target_email, status, initiated_by
                )
                VALUES (:id, :tenant_id, :realm_name, :workflow_type, :subject_user_id, :email, :status, :initiated_by)
            """),
            {
                "id": str(workflow_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "workflow_type": "leaver",
                "subject_user_id": "departing-user-123",
                "email": "departing@acme.com",
                "status": "pending",
                "initiated_by": test_user_a["id"]
            }
        )
        
        db_session.commit()
        
        # Verify workflow created
        result = db_session.execute(
            text("SELECT workflow_type, subject_user_id FROM jml_workflows WHERE id = :id"),
            {"id": str(workflow_id)}
        )
        
        workflow = result.fetchone()
        assert workflow is not None
        assert workflow[0] == "leaver"
        assert workflow[1] == "departing-user-123"
    
    def test_workflow_step_tracking(self, db_session, tenant_a):
        """Test tracking individual workflow steps."""
        workflow_id = uuid4()
        step_id = uuid4()
        
        # Create workflow
        db_session.execute(
            text("""
                INSERT INTO jml_workflows (id, tenant_id, realm_name, workflow_type, target_email, status, initiated_by)
                VALUES (:id, :tenant_id, :realm_name, 'joiner', 'test@test.com', 'in_progress', 'admin')
            """),
            {"id": str(workflow_id), "tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        # Create step
        db_session.execute(
            text("""
                INSERT INTO jml_workflow_steps (
                    id, workflow_id, step_name, step_type, step_order, status
                )
                VALUES (:id, :workflow_id, :step_name, :step_type, :step_order, :status)
            """),
            {
                "id": str(step_id),
                "workflow_id": str(workflow_id),
                "step_name": "Create User Account",
                "step_type": "create_user",
                "step_order": 1,
                "status": "completed"
            }
        )
        
        db_session.commit()
        
        # Verify step tracking
        result = db_session.execute(
            text("SELECT step_name, step_type, status FROM jml_workflow_steps WHERE id = :id"),
            {"id": str(step_id)}
        )
        
        step = result.fetchone()
        assert step is not None
        assert step[0] == "Create User Account"
        assert step[1] == "create_user"
        assert step[2] == "completed"


class TestMFAEnforcement:
    """Test MFA enforcement policy functionality."""
    
    def test_create_mfa_policy(self, db_session, tenant_a):
        """Test creating an MFA enforcement policy."""
        policy_id = uuid4()
        
        db_session.execute(
            text("""
                INSERT INTO mfa_enforcement_policies (
                    id, tenant_id, realm_name, policy_name,
                    enforcement_scope, enforcement_type, is_active
                )
                VALUES (:id, :tenant_id, :realm_name, :policy_name, :scope, :type, :is_active)
            """),
            {
                "id": str(policy_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "policy_name": "MFA Required for Admins",
                "scope": "privileged_roles",
                "type": "required",
                "is_active": True
            }
        )
        
        db_session.commit()
        
        # Verify policy created
        result = db_session.execute(
            text("SELECT policy_name, enforcement_scope FROM mfa_enforcement_policies WHERE id = :id"),
            {"id": str(policy_id)}
        )
        
        policy = result.fetchone()
        assert policy is not None
        assert policy[0] == "MFA Required for Admins"
        assert policy[1] == "privileged_roles"
    
    def test_track_user_mfa_status(self, db_session, tenant_a):
        """Test tracking user MFA status."""
        db_session.execute(
            text("""
                INSERT INTO user_mfa_status (
                    tenant_id, realm_name, user_id, user_email,
                    mfa_enabled, mfa_methods, enforcement_status
                )
                VALUES (:tenant_id, :realm_name, :user_id, :email, :mfa_enabled, :methods, :status)
            """),
            {
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "user_id": "user-123",
                "email": "user@acme.com",
                "mfa_enabled": True,
                "methods": ["totp", "webauthn"],
                "status": "compliant"
            }
        )
        
        db_session.commit()
        
        # Query MFA coverage for tenant
        result = db_session.execute(
            text("""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE mfa_enabled = true) as enabled,
                       COUNT(*) FILTER (WHERE enforcement_status = 'compliant') as compliant
                FROM user_mfa_status
                WHERE tenant_id = :tenant_id AND realm_name = :realm_name
            """),
            {"tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        stats = result.fetchone()
        assert stats[0] == 1  # total
        assert stats[1] == 1  # enabled
        assert stats[2] == 1  # compliant
    
    def test_mfa_compliance_violation(self, db_session, tenant_a):
        """Test recording MFA compliance violations."""
        policy_id = uuid4()
        violation_id = uuid4()
        
        # Create policy
        db_session.execute(
            text("""
                INSERT INTO mfa_enforcement_policies (id, tenant_id, realm_name, policy_name, enforcement_scope, enforcement_type)
                VALUES (:id, :tenant_id, :realm_name, 'MFA Required', 'all_users', 'required')
            """),
            {"id": str(policy_id), "tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        # Record violation
        db_session.execute(
            text("""
                INSERT INTO mfa_compliance_violations (
                    id, tenant_id, realm_name, user_id, user_email,
                    policy_id, violation_type, violation_description, status
                )
                VALUES (:id, :tenant_id, :realm_name, :user_id, :email, :policy_id, :type, :description, :status)
            """),
            {
                "id": str(violation_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "user_id": "user-456",
                "email": "noncompliant@acme.com",
                "policy_id": str(policy_id),
                "type": "not_configured",
                "description": "MFA not configured after grace period",
                "status": "open"
            }
        )
        
        db_session.commit()
        
        # Query violations
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM mfa_compliance_violations
                WHERE tenant_id = :tenant_id AND status = 'open'
            """),
            {"tenant_id": str(tenant_a["id"])}
        )
        
        count = result.fetchone()[0]
        assert count == 1


class TestAuditLogging:
    """Test audit logging functionality."""
    
    def test_audit_logger_initialization(self):
        """Test audit logger can be initialized."""
        from backend.libs.sg_core.audit_logger import AuditLogger
        
        logger = AuditLogger()
        assert logger is not None
    
    def test_log_audit_event(self, db_session, tenant_a, test_user_a):
        """Test logging an audit event."""
        from backend.libs.sg_core.audit_logger import AuditLogger, AuditAction
        
        logger = AuditLogger(db_session)
        
        # Log event
        audit_id = logger.log(
            action=AuditAction.USER_CREATED,
            tenant_id=tenant_a["id"],
            realm_name=tenant_a["realm"],
            actor_user_id=test_user_a["id"],
            actor_email=test_user_a["email"],
            resource_type="user",
            resource_id="new-user-123",
            resource_name="newuser@acme.com",
            before_state=None,
            after_state={"email": "newuser@acme.com", "enabled": True}
        )
        
        assert audit_id is not None
        
        # Verify audit log created
        result = db_session.execute(
            text("SELECT action, resource_type, resource_id FROM platform_audit_logs WHERE id = :id"),
            {"id": str(audit_id)}
        )
        
        log = result.fetchone()
        assert log is not None
        assert log[0] == "user_created"
        assert log[1] == "user"
        assert log[2] == "new-user-123"
    
    def test_audit_change_tracking(self, db_session, tenant_a, test_user_a):
        """Test tracking changes in audit logs."""
        from backend.libs.sg_core.audit_logger import AuditLogger, AuditAction
        
        logger = AuditLogger(db_session)
        
        before = {"email": "user@acme.com", "enabled": True, "roles": ["USER"]}
        after = {"email": "user@acme.com", "enabled": True, "roles": ["USER", "ADMIN"]}
        
        # Log change
        audit_id = logger.log(
            action=AuditAction.ROLE_ASSIGNED,
            tenant_id=tenant_a["id"],
            realm_name=tenant_a["realm"],
            actor_user_id=test_user_a["id"],
            actor_email=test_user_a["email"],
            resource_type="user",
            resource_id="user-123",
            before_state=before,
            after_state=after
        )
        
        # Verify changes calculated
        result = db_session.execute(
            text("SELECT changes FROM platform_audit_logs WHERE id = :id"),
            {"id": str(audit_id)}
        )
        
        log = result.fetchone()
        changes = log[0]
        
        assert changes is not None
        assert "roles" in changes
        assert changes["roles"]["before"] == ["USER"]
        assert changes["roles"]["after"] == ["USER", "ADMIN"]


class TestEvidenceCollection:
    """Test evidence collection functionality."""
    
    def test_create_evidence_package(self, db_session, tenant_a):
        """Test creating an evidence package."""
        package_id = uuid4()
        
        db_session.execute(
            text("""
                INSERT INTO evidence_packages (
                    id, tenant_id, realm_name, package_name,
                    report_period_start, report_period_end, created_by, status
                )
                VALUES (:id, :tenant_id, :realm_name, :name, :start, :end, :created_by, :status)
            """),
            {
                "id": str(package_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "name": "Q4 2025 SOC 2 Evidence",
                "start": "2025-10-01",
                "end": "2025-12-31",
                "created_by": "compliance@acme.com",
                "status": "collecting"
            }
        )
        
        db_session.commit()
        
        # Verify package created
        result = db_session.execute(
            text("SELECT package_name, status FROM evidence_packages WHERE id = :id"),
            {"id": str(package_id)}
        )
        
        package = result.fetchone()
        assert package is not None
        assert package[0] == "Q4 2025 SOC 2 Evidence"
        assert package[1] == "collecting"
    
    def test_add_evidence_items(self, db_session, tenant_a):
        """Test adding evidence items to a package."""
        package_id = uuid4()
        item_id = uuid4()
        
        # Create package
        db_session.execute(
            text("""
                INSERT INTO evidence_packages (id, tenant_id, realm_name, package_name, report_period_start, report_period_end, created_by)
                VALUES (:id, :tenant_id, :realm_name, 'Test Package', '2025-11-01', '2025-11-30', 'admin')
            """),
            {"id": str(package_id), "tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        # Add evidence item
        db_session.execute(
            text("""
                INSERT INTO evidence_items (
                    id, package_id, tenant_id, realm_name,
                    evidence_type, evidence_title, file_path, file_hash,
                    source_system, collected_by
                )
                VALUES (:id, :package_id, :tenant_id, :realm_name, :type, :title, :path, :hash, :source, :collected_by)
            """),
            {
                "id": str(item_id),
                "package_id": str(package_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "type": "report",
                "title": "Access Review Report Q4 2025",
                "path": "s3://evidence/access_review_q4.pdf",
                "hash": "abc123" * 10,  # SHA-256 placeholder
                "source": "iam_agent",
                "collected_by": "system"
            }
        )
        
        db_session.commit()
        
        # Verify evidence added
        result = db_session.execute(
            text("SELECT evidence_title, source_system FROM evidence_items WHERE id = :id"),
            {"id": str(item_id)}
        )
        
        item = result.fetchone()
        assert item is not None
        assert item[0] == "Access Review Report Q4 2025"
        assert item[1] == "iam_agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

