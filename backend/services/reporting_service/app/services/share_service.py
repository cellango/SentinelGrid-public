"""Report sharing service - manages shareable links."""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.report import Report, ReportShare
from app.core.config import settings

logger = logging.getLogger(__name__)


class ShareService:
    """Service for managing report shares."""
    
    def create_share(
        self,
        db: Session,
        report_id: str,
        tenant_id: str,
        expires_in_days: int = 7,
        password: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> ReportShare:
        """
        Create a shareable link for a report.
        
        Args:
            db: Database session
            report_id: Report ID
            tenant_id: Tenant ID
            expires_in_days: Number of days until expiration
            password: Optional password for protection
            created_by: User ID who created the share
            
        Returns:
            ReportShare record
        """
        # Verify report exists and belongs to tenant
        report = db.query(Report).filter(
            Report.id == report_id,
            Report.tenant_id == tenant_id
        ).first()
        
        if not report:
            raise ValueError(f"Report {report_id} not found or not accessible")
        
        # Generate unique share token
        share_token = secrets.token_urlsafe(32)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Hash password if provided
        password_hash = None
        if password:
            password_hash = self._hash_password(password)
        
        # Create share record
        share = ReportShare(
            report_id=report_id,
            tenant_id=tenant_id,
            share_token=share_token,
            expires_at=expires_at,
            password_hash=password_hash,
            created_by=created_by
        )
        
        db.add(share)
        db.commit()
        db.refresh(share)
        
        logger.info(f"Created share {share.id} for report {report_id}")
        return share
    
    def get_share(self, db: Session, share_token: str) -> Optional[ReportShare]:
        """Get a share by token."""
        share = self.get_share_record(db, share_token)

        if not share:
            return None

        # Check expiration
        if self.is_expired(share):
            logger.warning(f"Share {share.id} has expired")
            return None

        return share

    def get_share_record(self, db: Session, share_token: str) -> Optional[ReportShare]:
        """Get a share by token without applying expiration checks."""
        share = db.query(ReportShare).filter(
            ReportShare.share_token == share_token
        ).first()
        return share

    def is_expired(self, share: ReportShare) -> bool:
        """Return whether a share is expired."""
        if not share.expires_at:
            return False
        now = (
            datetime.now(share.expires_at.tzinfo)
            if share.expires_at.tzinfo
            else datetime.utcnow()
        )
        return share.expires_at < now
    
    def verify_password(self, share: ReportShare, password: str) -> bool:
        """Verify password for a protected share."""
        if not share.password_hash:
            return True  # No password required
        
        return self._verify_password(password, share.password_hash)
    
    def access_share(self, db: Session, share: ReportShare):
        """Record access to a share."""
        share.access_count += 1
        share.last_accessed_at = datetime.utcnow()
        db.commit()
    
    def delete_share(self, db: Session, share_id: str, tenant_id: str):
        """Delete a share."""
        share = db.query(ReportShare).filter(
            ReportShare.id == share_id,
            ReportShare.tenant_id == tenant_id
        ).first()
        
        if not share:
            raise ValueError(f"Share {share_id} not found")
        
        db.delete(share)
        db.commit()
        logger.info(f"Deleted share {share_id}")
    
    def list_shares(self, db: Session, report_id: Optional[str] = None, tenant_id: Optional[str] = None) -> list:
        """List shares, optionally filtered by report or tenant."""
        query = db.query(ReportShare)
        
        if report_id:
            query = query.filter(ReportShare.report_id == report_id)
        if tenant_id:
            query = query.filter(ReportShare.tenant_id == tenant_id)
        
        return query.order_by(ReportShare.created_at.desc()).all()
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256 (simple hashing for share passwords)."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against a hash."""
        return self._hash_password(password) == password_hash
    
    def generate_share_url(self, share_token: str) -> str:
        """Generate the full shareable URL."""
        base_url = settings.REPORT_STORAGE_URL.replace('/reports', '') or 'http://localhost:3000'
        return f"{base_url}/shared/{share_token}"
