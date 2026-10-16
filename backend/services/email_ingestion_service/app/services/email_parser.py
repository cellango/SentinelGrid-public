"""Email parser for RFC 822 emails."""

import email
import re
from email.utils import parsedate_to_datetime, parseaddr
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import tldextract


class EmailParser:
    """Parser for RFC 822 emails."""
    
    def __init__(self):
        """Initialize email parser."""
        self.url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            re.IGNORECASE
        )
        self.ip_pattern = re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        )
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        self.hash_pattern = re.compile(
            r'\b[a-fA-F0-9]{32,64}\b'  # MD5, SHA1, SHA256
        )
    
    def parse(self, raw_email: str) -> Dict:
        """
        Parse RFC 822 email.
        
        Args:
            raw_email: Raw email string (RFC 822 format)
            
        Returns:
            Dictionary with parsed email data
        """
        msg = email.message_from_string(raw_email)
        
        # Extract headers
        message_id = msg.get("Message-ID", "").strip()
        subject = msg.get("Subject", "")
        from_addr = self._parse_address(msg.get("From", ""))
        to_addr = self._parse_address(msg.get("To", ""))
        reply_to = self._parse_address(msg.get("Reply-To", ""))
        
        # Parse date
        date_str = msg.get("Date", "")
        received_date = None
        if date_str:
            try:
                received_date = parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                pass
        
        # Extract body
        html_body, text_body = self._extract_body(msg)
        
        # Extract attachments
        attachments = self._extract_attachments(msg)
        
        # Extract reported_by from forwarded email
        reported_by = self._extract_reported_by(msg)
        
        return {
            "message_id": message_id,
            "subject": subject,
            "from_address": from_addr,
            "to_address": to_addr,
            "reply_to": reply_to,
            "received_date": received_date,
            "reported_by": reported_by,
            "html_body": html_body,
            "text_body": text_body,
            "attachments": attachments,
            "raw_email": raw_email
        }
    
    def _parse_address(self, address_str: str) -> str:
        """Parse email address from header."""
        if not address_str:
            return ""
        
        name, addr = parseaddr(address_str)
        return addr if addr else address_str.strip()
    
    def _extract_body(self, msg: email.message.Message) -> Tuple[Optional[str], Optional[str]]:
        """Extract HTML and text body from email."""
        html_body = None
        text_body = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/html" and not html_body:
                    html_body = part.get_payload(decode=True)
                    if html_body:
                        html_body = html_body.decode("utf-8", errors="ignore")
                
                elif content_type == "text/plain" and not text_body:
                    text_body = part.get_payload(decode=True)
                    if text_body:
                        text_body = text_body.decode("utf-8", errors="ignore")
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            
            if payload:
                payload = payload.decode("utf-8", errors="ignore")
                
                if content_type == "text/html":
                    html_body = payload
                elif content_type == "text/plain":
                    text_body = payload
        
        return html_body, text_body
    
    def _extract_attachments(self, msg: email.message.Message) -> List[Dict]:
        """Extract attachment metadata."""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    content_type = part.get_content_type()
                    size = len(part.get_payload(decode=True) or b"")
                    
                    attachments.append({
                        "filename": filename,
                        "content_type": content_type,
                        "size": size
                    })
        
        return attachments
    
    def _extract_reported_by(self, msg: email.message.Message) -> Optional[str]:
        """Extract reporter email from forwarded email."""
        # Check for X-Forwarded-From or similar headers
        forwarded_from = msg.get("X-Forwarded-From") or msg.get("X-Original-From")
        if forwarded_from:
            return self._parse_address(forwarded_from)
        
        # Check body for "From:" in forwarded emails
        text_body = None
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    text_body = part.get_payload(decode=True)
                    if text_body:
                        text_body = text_body.decode("utf-8", errors="ignore")
                    break
        else:
            if msg.get_content_type() == "text/plain":
                text_body = msg.get_payload(decode=True)
                if text_body:
                    text_body = text_body.decode("utf-8", errors="ignore")
        
        if text_body:
            # Look for "From:" pattern in forwarded email body
            from_match = re.search(r'From:\s*([^\n\r]+)', text_body, re.IGNORECASE)
            if from_match:
                return self._parse_address(from_match.group(1))
        
        return None
    
    def extract_urls(self, html_body: Optional[str], text_body: Optional[str]) -> List[str]:
        """Extract URLs from email body."""
        urls = set()
        
        # Extract from HTML
        if html_body:
            soup = BeautifulSoup(html_body, "html.parser")
            
            # Extract from <a> tags
            for link in soup.find_all("a", href=True):
                urls.add(link["href"])
            
            # Extract from text content
            text_content = soup.get_text()
            urls.update(self.url_pattern.findall(text_content))
        
        # Extract from text body
        if text_body:
            urls.update(self.url_pattern.findall(text_body))
        
        return list(urls)
    
    def extract_domains(self, urls: List[str], email_addresses: List[str]) -> List[str]:
        """Extract domains from URLs and email addresses."""
        domains = set()
        
        # Extract from URLs
        for url in urls:
            try:
                extracted = tldextract.extract(url)
                if extracted.domain:
                    domain = f"{extracted.domain}.{extracted.suffix}"
                    domains.add(domain)
            except Exception:
                pass
        
        # Extract from email addresses
        for email_addr in email_addresses:
            if "@" in email_addr:
                domain = email_addr.split("@")[1]
                domains.add(domain)
        
        return list(domains)
    
    def extract_ips(self, text: str) -> List[str]:
        """Extract IP addresses from text."""
        return list(set(self.ip_pattern.findall(text)))
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text."""
        return list(set(self.email_pattern.findall(text)))
    
    def extract_hashes(self, text: str) -> List[str]:
        """Extract file hashes from text."""
        return list(set(self.hash_pattern.findall(text)))

