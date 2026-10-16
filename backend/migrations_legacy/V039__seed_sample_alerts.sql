-- Migration: Seed Sample Alerts for Testing
-- Date: 2025-12-03
-- Purpose: Create sample security alerts for dashboard testing and development

-- Note: Alerts are created for the system tenant initially
-- In production, alerts come from SIEM/detection rules

-- Get or create a test tenant for sample data
DO $$ 
DECLARE
    test_tenant_id UUID;
BEGIN
    -- Try to find an existing tenant (not system)
    SELECT id INTO test_tenant_id FROM tenants WHERE slug != 'system' LIMIT 1;
    
    -- If no tenant exists, we'll use system tenant for now
    IF test_tenant_id IS NULL THEN
        test_tenant_id := '00000000-0000-0000-0000-000000000000';
    END IF;

    -- 1. Critical - Ransomware Detected
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'wazuh',
        'WZH-RANS-001',
        'Ransomware Activity Detected on Finance Workstation',
        'Multiple files with .encrypted extension detected. Suspicious process WannaCrypt.exe identified.',
        'critical',
        'open',
        NOW() - INTERVAL '2 hours',
        'finance-ws-042',
        'john.smith@company.com',
        '{"rule_id": "91816", "rule_name": "Ransomware patterns detected", "agent": {"id": "042", "name": "finance-ws-042"}}'::jsonb
    ) ON CONFLICT DO NOTHING;

    -- 2. High - Phishing Email Reported
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'email_gateway',
        'PHISH-REPORT-2024-1203-001',
        'User Reported Suspicious Email - CEO Impersonation',
        'User reported email claiming to be from CEO requesting urgent wire transfer. Sender domain mismatch detected.',
        'high',
        'open',
        NOW() - INTERVAL '4 hours',
        NULL,
        'sarah.johnson@company.com',
        '{"sender": "ceo@comp4ny.com", "subject": "URGENT: Wire Transfer Required", "reported_by": "sarah.johnson@company.com"}'::jsonb
    ) ON CONFLICT DO NOTHING;

    -- 3. High - Brute Force Attack
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'wazuh',
        'WZH-AUTH-002',
        'Multiple Failed Login Attempts - Brute Force Attack',
        'Account admin@company.com: 127 failed login attempts from 15 different IPs in 10 minutes.',
        'high',
        'investigating',
        NOW() - INTERVAL '6 hours',
        'vpn-gateway',
        'admin@company.com',
        '{"failed_attempts": 127, "source_ips": ["185.220.101.1", "45.142.212.61"], "timeframe_minutes": 10}'::jsonb
    ) ON CONFLICT DO NOTHING;

    -- 4. Medium - Suspicious Cloud API Activity
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'cloudtrail',
        'AWS-CT-2024-1203-045',
        'Unusual IAM Policy Changes from Unknown Location',
        'IAM policy modified to grant admin access from IP in suspicious region (Russia). User normally works from US West.',
        'medium',
        'open',
        NOW() - INTERVAL '8 hours',
        'aws-account-prod',
        'deploy.bot@company.com',
        '{"event_name": "PutUserPolicy", "source_ip": "185.220.102.34", "region": "us-east-1", "normal_location": "us-west-2"}'::jsonb
    ) ON CONFLICT DO NOTHING;

    -- 5. High - Malware Detected on Endpoint
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'wazuh',
        'WZH-MAL-003',
        'Trojan Horse Detected - Engineering Laptop',
        'ClamAV detected Win.Trojan.Generic on engineering laptop. File quarantined but process may have executed.',
        'high',
        'open',
        NOW() - INTERVAL '12 hours',
        'eng-laptop-087',
        'mike.wilson@company.com',
        '{"malware_type": "Trojan", "file_path": "/home/mike/downloads/invoice.pdf.exe", "scanner": "ClamAV"}'::jsonb
    ) ON CONFLICT DO NOTHING;

    -- 6. Critical - Public S3 Bucket with Sensitive Data
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'prowler',
        'PROWLER-S3-001',
        'S3 Bucket Publicly Accessible - Customer PII Exposed',
        'Bucket customer-data-prod contains files with PII and is publicly readable. 12,450 customer records potentially exposed.',
        'critical',
        'open',
        NOW() - INTERVAL '1 hour',
        'customer-data-prod',
        'devops@company.com',
        '{"bucket": "customer-data-prod", "region": "us-east-1", "records_count": 12450, "contains_pii": true}'::jsonb
    ) ON CONFLICT DO NOTHING;

    -- 7. Medium - Unusual Data Download
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'dlp',
        'DLP-EXFIL-001',
        'Large Data Download - Employee Offboarding',
        'Employee downloaded 45GB of company data 2 days before resignation date. Includes customer database backup.',
        'medium',
        'investigating',
        NOW() - INTERVAL '15 hours',
        'fileserver-prod',
        'leaving.employee@company.com',
        '{"data_size_gb": 45, "files_downloaded": 340, "resignation_date": "2024-12-05", "includes_db_backup": true}'::jsonb
    ) ON CONFLICT DO NOTHING;

    -- 8. Low - Failed MFA Enrollment
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'okta',
        'OKTA-MFA-001',
        'Multiple Failed MFA Enrollment Attempts',
        'User attempted to enroll MFA device 8 times without success. May need IT assistance.',
        'low',
        'open',
        NOW() - INTERVAL '20 hours',
        NULL,
        'new.employee@company.com',
        '{"enrollment_attempts": 8, "mfa_type": "totp", "user_new_hire": true}'::jsonb
    ) ON CONFLICT DO NOTHING;

    -- 9. High - Credential Dump Detected
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'wazuh',
        'WZH-CRED-001',
        'Credential Dumping Activity - Mimikatz Detected',
        'Mimikatz execution detected on domain controller. Potential credential theft in progress.',
        'critical',
        'open',
        NOW() - INTERVAL '30 minutes',
        'dc-01',
        'SYSTEM',
        '{"tool": "mimikatz.exe", "technique": "LSASS Memory Dump", "mitre_id": "T1003.001"}'::jsonb
    ) ON CONFLICT DO NOTHING;

    -- 10. Medium - Suspicious Admin Login
    INSERT INTO alerts (tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload)
    VALUES (
        test_tenant_id,
        'azure_ad',
        'AAD-LOGIN-001',
        'Admin Login from Unusual Location - Outside Business Hours',
        'Global admin logged in from Vietnam at 2:00 AM local time. User typically works from California during business hours.',
        'medium',
        'open',
        NOW() - INTERVAL '5 hours',
        NULL,
        'global.admin@company.com',
        '{"location": "Hanoi, Vietnam", "time_local": "02:00", "usual_location": "San Francisco, CA", "usual_hours": "09:00-18:00"}'::jsonb
    ) ON CONFLICT DO NOTHING;

END $$;

-- Add comments
COMMENT ON TABLE alerts IS 'Security alerts from SIEM, detection rules, and security tools';

