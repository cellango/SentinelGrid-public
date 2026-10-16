"""
Audit logging service for security events.
Logs all authentication and authorization events for compliance.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit logging."""
    
    _db_engine = None
    _SessionLocal = None
    
    @classmethod
    def _get_db_session(cls):
        """Get database session (lazy initialization)."""
        if cls._db_engine is None:
            if not settings.DB_URL:
                logger.warning("DB_URL not configured, audit logging disabled")
                return None
            
            cls._db_engine = create_engine(settings.DB_URL)
            cls._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls._db_engine)
        
        return cls._SessionLocal()
    
    @staticmethod
    def log_auth_event(
        realm_name: str,
        action: str,
        actor_user_id: Optional[str] = None,
        actor_email: Optional[str] = None,
        customer_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log authentication event to audit log.
        
        Args:
            realm_name: Keycloak realm name
            action: Action type (user_login, user_logout, user_signup, token_refresh, etc.)
            actor_user_id: Keycloak user ID
            actor_email: User email
            customer_id: Customer UUID
            organization_id: Organization UUID
            details: Additional context (JSON)
            ip_address: Client IP address
            user_agent: Client user agent
        """
        try:
            db = AuditService._get_db_session()
            if db is None:
                # Database not configured, skip audit logging
                return
            
            try:
                db.execute(
                    text("""
                        INSERT INTO realm_audit_log (
                            realm_name, customer_id, organization_id, action,
                            actor_user_id, actor_email, details, ip_address, user_agent, created_at
                        ) VALUES (
                            :realm_name, :customer_id, :organization_id, :action,
                            :actor_user_id, :actor_email, :details, :ip_address, :user_agent, :created_at
                        )
                    """),
                    {
                        "realm_name": realm_name,
                        "customer_id": customer_id,
                        "organization_id": organization_id,
                        "action": action,
                        "actor_user_id": actor_user_id,
                        "actor_email": actor_email,
                        "details": json.dumps(details) if details else None,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "created_at": datetime.utcnow()
                    }
                )
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error writing audit log: {e}", exc_info=True)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error creating audit log session: {e}", exc_info=True)
