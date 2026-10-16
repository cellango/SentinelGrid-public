"""IMAP client for email polling."""

import imaplib
import email
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IMAPClient:
    """IMAP client for polling email inbox."""
    
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        use_ssl: bool = True,
        mailbox: str = "INBOX"
    ):
        """Initialize IMAP client."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        self.mailbox = mailbox
        self.connection: Optional[imaplib.IMAP4_SSL] = None
    
    def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            if self.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self.connection = imaplib.IMAP4(self.host, self.port)
            
            self.connection.login(self.user, self.password)
            self.connection.select(self.mailbox)
            
            logger.info(f"Connected to IMAP server {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except Exception as e:
                logger.error(f"Error disconnecting from IMAP: {e}")
            finally:
                self.connection = None
    
    def fetch_unread_emails(self, since_date: Optional[datetime] = None) -> List[str]:
        """
        Fetch unread emails from mailbox.
        
        Args:
            since_date: Only fetch emails since this date
            
        Returns:
            List of raw email strings (RFC 822 format)
        """
        if not self.connection:
            if not self.connect():
                return []
        
        emails = []
        
        try:
            # Search for unread emails
            if since_date:
                date_str = since_date.strftime("%d-%b-%Y")
                status, messages = self.connection.search(None, f'UNSEEN SINCE {date_str}')
            else:
                status, messages = self.connection.search(None, "UNSEEN")
            
            if status != "OK":
                logger.error("Failed to search for emails")
                return []
            
            email_ids = messages[0].split()
            
            for email_id in email_ids:
                try:
                    # Fetch email
                    status, msg_data = self.connection.fetch(email_id, "(RFC822)")
                    
                    if status == "OK" and msg_data[0]:
                        raw_email = msg_data[0][1]
                        emails.append(raw_email.decode("utf-8", errors="ignore"))
                        
                        # Mark as read (optional - comment out if you want to keep unread)
                        # self.connection.store(email_id, "+FLAGS", "\\Seen")
                except Exception as e:
                    logger.error(f"Error fetching email {email_id}: {e}")
                    continue
            
            logger.info(f"Fetched {len(emails)} unread emails")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def mark_as_read(self, email_id: bytes):
        """Mark an email as read."""
        if not self.connection:
            return
        
        try:
            self.connection.store(email_id, "+FLAGS", "\\Seen")
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")

