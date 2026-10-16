"""Tests for email parser service."""

import pytest
from app.services.email_parser import EmailParser


class TestEmailParser:
    """Test email parser functionality."""
    
    def test_parse_simple_email(self):
        """Test parsing a simple email."""
        parser = EmailParser()
        raw_email = """From: attacker@example.com
To: victim@company.com
Subject: Urgent: Verify Your Account
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test123@example.com>

This is a test email with a malicious link: https://evil.com/phishing
"""
        result = parser.parse_email(raw_email)
        
        assert result["from_address"] == "attacker@example.com"
        assert result["to_address"] == "victim@company.com"
        assert result["subject"] == "Urgent: Verify Your Account"
        assert len(result["observables"]) > 0
        assert any(o["observable_type"] == "url" for o in result["observables"])
    
    def test_extract_urls(self):
        """Test URL extraction from email body."""
        parser = EmailParser()
        raw_email = """From: test@example.com
To: user@company.com
Subject: Test
Date: Mon, 1 Jan 2024 12:00:00 +0000

Visit https://malicious.com and http://evil.org for more info.
"""
        result = parser.parse_email(raw_email)
        
        urls = [o for o in result["observables"] if o["observable_type"] == "url"]
        assert len(urls) >= 2
        assert any("malicious.com" in o["observable_value"] for o in urls)
        assert any("evil.org" in o["observable_value"] for o in urls)
    
    def test_extract_domains(self):
        """Test domain extraction from email."""
        parser = EmailParser()
        raw_email = """From: sender@suspicious-domain.com
To: user@company.com
Subject: Test
Date: Mon, 1 Jan 2024 12:00:00 +0000

Check out https://phishing-site.net
"""
        result = parser.parse_email(raw_email)
        
        domains = [o for o in result["observables"] if o["observable_type"] == "domain"]
        assert len(domains) > 0
        assert any("suspicious-domain.com" in o["observable_value"] for o in domains)
        assert any("phishing-site.net" in o["observable_value"] for o in domains)
    
    def test_extract_ips(self):
        """Test IP address extraction."""
        parser = EmailParser()
        raw_email = """From: test@example.com
To: user@company.com
Subject: Test
Date: Mon, 1 Jan 2024 12:00:00 +0000

Connect to 192.168.1.100 for access.
"""
        result = parser.parse_email(raw_email)
        
        ips = [o for o in result["observables"] if o["observable_type"] == "ip"]
        assert len(ips) > 0
        assert any("192.168.1.100" in o["observable_value"] for o in ips)
    
    def test_extract_hashes(self):
        """Test hash extraction."""
        parser = EmailParser()
        raw_email = """From: test@example.com
To: user@company.com
Subject: Test
Date: Mon, 1 Jan 2024 12:00:00 +0000

File hash: 5d41402abc4b2a76b9719d911017c592
SHA256: 2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae
"""
        result = parser.parse_email(raw_email)
        
        hashes = [o for o in result["observables"] if o["observable_type"] == "hash"]
        assert len(hashes) >= 2
    
    def test_extract_attachments(self):
        """Test attachment extraction."""
        parser = EmailParser()
        raw_email = """From: test@example.com
To: user@company.com
Subject: Test
Date: Mon, 1 Jan 2024 12:00:00 +0000
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain

Email body

--boundary123
Content-Type: application/pdf
Content-Disposition: attachment; filename="malicious.pdf"

PDF content here
--boundary123--
"""
        result = parser.parse_email(raw_email)
        
        assert len(result["attachments"]) > 0
        assert any(att.get("filename") == "malicious.pdf" for att in result["attachments"])
    
    def test_extract_reported_by(self):
        """Test extraction of original reporter from forwarded email."""
        parser = EmailParser()
        raw_email = """From: security@company.com
To: admin@company.com
Subject: Fwd: Suspicious Email
Date: Mon, 1 Jan 2024 12:00:00 +0000
X-Forwarded-For: original@company.com

-----Original Message-----
From: original@company.com
To: security@company.com
Subject: Suspicious Email

This looks suspicious.
"""
        result = parser.parse_email(raw_email)
        
        # Should extract original reporter
        assert result.get("reported_by") is not None

