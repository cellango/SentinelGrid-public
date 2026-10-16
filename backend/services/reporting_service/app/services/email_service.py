"""Email delivery service for scheduled reports."""

import logging
from typing import List, Optional
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from app.core.config import settings
from app.models.report import Report

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending report emails."""
    
    def __init__(self):
        # Email configuration from environment
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.use_tls = settings.SMTP_USE_TLS
    
    async def send_report_email(
        self,
        report: Report,
        recipients: List[str],
        subject: Optional[str] = None,
        message: Optional[str] = None
    ) -> bool:
        """
        Send a report via email.
        
        Args:
            report: Report record
            recipients: List of email addresses
            subject: Optional custom subject
            message: Optional custom message body
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not recipients:
            logger.warning("No recipients provided for report email")
            return False
        
        if not report.download_url and not report.file_path:
            logger.error(f"Report {report.id} has no file to attach")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject or f"SentinelGrid Report: {report.name}"
            
            # Email body
            body = message or f"""
Hello,

Please find attached your {report.name} report.

Report Details:
- Format: {report.format.upper()}
- Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if report.generated_at else 'N/A'}
- Status: {report.status}

You can also download this report directly from your SentinelGrid dashboard.

Best regards,
SentinelGrid Team
"""
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach report file
            if report.file_path and Path(report.file_path).exists():
                file_path = Path(report.file_path)
                with open(file_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {file_path.name}'
                )
                msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                
                text = msg.as_string()
                server.sendmail(self.from_email, recipients, text)
            
            logger.info(f"Sent report {report.id} to {len(recipients)} recipients")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send report email: {e}", exc_info=True)
            return False


# Global email service instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create the global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

