# Standard SOC Playbooks for Vector Database

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-11-28  
**Purpose:** Standard incident response playbooks to be stored in vector database for RAG retrieval

---

## Playbook Structure

Each playbook follows this structure for optimal RAG retrieval:

```json
{
  "playbook_id": "unique-id",
  "name": "Playbook Name",
  "category": "incident_response|threat_hunting|vulnerability_management",
  "description": "Brief description",
  "mitre_tactics": ["Tactic1", "Tactic2"],
  "mitre_techniques": ["T1059", "T1547"],
  "nist_controls": ["IR-4", "SI-3"],
  "owasp_categories": ["A01", "A07"],
  "severity_levels": ["high", "critical"],
  "estimated_duration": "X hours",
  "required_roles": ["SOC_ANALYST", "SOC_MANAGER"],
  "steps": [...],
  "automation_opportunities": [...],
  "lessons_learned_template": "..."
}
```

---

## 1. Malware Detection & Response Playbook

**Playbook ID:** `malware-response-v1`

**Description:**
Comprehensive playbook for detecting, containing, and eradicating malware infections across endpoints and networks.

**MITRE Mappings:**
- **Tactics:** Execution, Persistence, Defense Evasion, Command and Control
- **Techniques:** T1059 (Command and Scripting Interpreter), T1547 (Boot or Logon Autostart Execution), T1070 (Indicator Removal)

**NIST Controls:**
- IR-4 (Incident Handling)
- SI-3 (Malicious Code Protection)
- IR-5 (Incident Monitoring)

**Steps:**
1. **Detection & Triage**
   - EDR/SIEM alert analysis
   - Hash lookup (VirusTotal, etc.)
   - Behavioral analysis
   - Output: Malware hash, affected hosts, infection vector

2. **Containment (Immediate)**
   - Network isolation of affected systems
   - Disable compromised accounts
   - Block malicious IPs/domains
   - Approval: SOC Manager

3. **Investigation**
   - Timeline reconstruction
   - Artifact collection (memory, disk, logs)
   - IOC extraction
   - Output: Full incident timeline, IOCs

4. **Eradication**
   - Malware removal
   - Registry/startup cleanup
   - Service removal
   - Output: Cleaned systems list

5. **Recovery**
   - System restoration from clean backup
   - Security hardening
   - Monitoring enhancement
   - Output: Restored systems, enhanced monitoring

6. **Post-Incident**
   - Lessons learned
   - Detection rule updates
   - Security awareness training
   - Output: Updated playbook, new detection rules

**Automation Opportunities:**
- Auto-isolation on high-confidence detections
- IOC extraction and threat intel enrichment
- Automated malware analysis (sandbox)

---

## 2. Phishing Incident Response Playbook

**Playbook ID:** `phishing-response-v1`

**Description:**
Response procedures for phishing attacks, including email analysis, user notification, and account compromise assessment.

**MITRE Mappings:**
- **Tactics:** Initial Access, Collection, Exfiltration
- **Techniques:** T1566 (Phishing), T1071 (Application Layer Protocol)

**NIST Controls:**
- IR-4 (Incident Handling)
- AT-2 (Security Awareness Training)
- AC-2 (Account Management)

**Steps:**
1. **Email Analysis**
   - Header analysis
   - Link/attachment analysis
   - Sender reputation check
   - Output: Phishing indicators, malicious URLs

2. **User Notification**
   - Identify affected users
   - Send security alert
   - Provide reporting instructions
   - Output: Notified users list

3. **Link/Attachment Analysis**
   - URL reputation check
   - Sandbox analysis
   - File hash analysis
   - Output: Threat assessment

4. **Account Compromise Assessment**
   - Check for credential harvesting
   - Review login logs
   - Check for data exfiltration
   - Output: Compromise status

5. **Remediation**
   - Block malicious domains/URLs
   - Reset compromised credentials
   - Enable MFA (if not already)
   - Output: Remediation actions taken

**Automation Opportunities:**
- Automated email header analysis
- URL reputation checking
- User notification automation

---

## 3. Data Breach Response Playbook

**Playbook ID:** `data-breach-response-v1`

**Description:**
Comprehensive data breach response including detection, impact assessment, regulatory notification, and recovery.

**MITRE Mappings:**
- **Tactics:** Collection, Exfiltration
- **Techniques:** T1005 (Data from Local System), T1041 (Exfiltration Over C2 Channel)

**NIST Controls:**
- IR-4 (Incident Handling)
- IR-6 (Incident Reporting)
- CP-4 (Contingency Plan Testing)

**Steps:**
1. **Breach Detection**
   - Identify breach indicators
   - Determine breach scope
   - Preserve evidence
   - Output: Breach timeline, affected systems

2. **Impact Assessment**
   - Identify compromised data types
   - Assess data sensitivity (PII, PHI, etc.)
   - Determine affected individuals
   - Output: Impact assessment report

3. **Containment**
   - Isolate affected systems
   - Revoke compromised credentials
   - Block exfiltration channels
   - Output: Containment actions

4. **Regulatory Notification**
   - Determine notification requirements (GDPR, HIPAA, etc.)
   - Prepare notification letters
   - Coordinate with legal/compliance
   - Output: Notification status

5. **Recovery**
   - System restoration
   - Security hardening
   - Enhanced monitoring
   - Output: Recovery status

6. **Post-Incident**
   - Root cause analysis
   - Security improvements
   - Regulatory reporting
   - Output: Final report

**Automation Opportunities:**
- Automated data classification
- Notification template generation
- Regulatory requirement checking

---

## 4. Ransomware Response Playbook

**Playbook ID:** `ransomware-response-v1`

**Description:**
Response procedures for ransomware attacks, including detection, isolation, backup verification, and recovery.

**MITRE Mappings:**
- **Tactics:** Impact
- **Techniques:** T1486 (Data Encrypted for Impact), T1490 (Inhibit System Recovery)

**NIST Controls:**
- IR-4 (Incident Handling)
- CP-9 (System Backup)
- SI-3 (Malicious Code Protection)

**Steps:**
1. **Detection & Isolation**
   - Identify ransomware indicators
   - Immediate network isolation
   - Disable affected accounts
   - Output: Isolated systems list

2. **Backup Verification**
   - Verify backup integrity
   - Check backup recency
   - Test backup restoration
   - Output: Backup status

3. **Negotiation Considerations** (if applicable)
   - Legal review
   - Risk assessment
   - Decision framework
   - Output: Decision and rationale

4. **Recovery Procedures**
   - System restoration from backup
   - Verify system integrity
   - Security hardening
   - Output: Recovered systems

5. **Prevention Measures**
   - Patch vulnerabilities
   - Enhance monitoring
   - Security awareness
   - Output: Prevention actions

**Automation Opportunities:**
- Automated backup verification
- System isolation automation
- Recovery orchestration

---

## 5. Privilege Escalation Response Playbook

**Playbook ID:** `privilege-escalation-response-v1`

**Description:**
Response to privilege escalation attempts, including detection, containment, access review, and system hardening.

**MITRE Mappings:**
- **Tactics:** Privilege Escalation
- **Techniques:** T1078 (Valid Accounts), T1548 (Abuse Elevation Control Mechanism)

**NIST Controls:**
- AC-6 (Least Privilege)
- AC-2 (Account Management)
- AU-6 (Audit Review)

**Steps:**
1. **Detection**
   - Identify privilege escalation indicators
   - Review access logs
   - Analyze role changes
   - Output: Escalation details

2. **Immediate Containment**
   - Revoke escalated privileges
   - Disable compromised accounts
   - Isolate affected systems
   - Output: Containment actions

3. **Access Review**
   - Review all user privileges
   - Identify over-privileged accounts
   - Review role assignments
   - Output: Access review report

4. **System Hardening**
   - Apply least privilege
   - Remove unnecessary privileges
   - Enhance monitoring
   - Output: Hardening actions

5. **Monitoring Enhancement**
   - Add privilege escalation alerts
   - Enhance audit logging
   - Output: Enhanced monitoring rules

**Automation Opportunities:**
- Automated privilege revocation
- Access review automation
- Alert generation

---

## 6. Suspicious Login Activity Playbook

**Playbook ID:** `suspicious-login-response-v1`

**Description:**
Response to suspicious login activities including unusual locations, time-based anomalies, and account compromise.

**MITRE Mappings:**
- **Tactics:** Initial Access
- **Techniques:** T1078 (Valid Accounts), T1110 (Brute Force)

**NIST Controls:**
- AC-7 (Unsuccessful Logon Attempts)
- IA-2 (Identification and Authentication)
- AU-2 (Audit Events)

**Steps:**
1. **Anomaly Detection**
   - Unusual location detection
   - Time-based anomalies
   - Device fingerprinting
   - Output: Anomaly details

2. **Account Verification**
   - Contact user for verification
   - Check for account compromise
   - Review recent activity
   - Output: Verification status

3. **Account Protection**
   - Temporary account lockout
   - Require password reset
   - Enable MFA (if not already)
   - Output: Protection actions

4. **Investigation**
   - Review login history
   - Check for credential theft
   - Analyze access patterns
   - Output: Investigation report

5. **Remediation**
   - Reset credentials
   - Revoke sessions
   - Security awareness
   - Output: Remediation actions

**Automation Opportunities:**
- Automated account lockout
- User notification
- Session revocation

---

## 7. DDoS Attack Response Playbook

**Playbook ID:** `ddos-response-v1`

**Description:**
Response procedures for distributed denial-of-service attacks, including detection, mitigation, and service restoration.

**MITRE Mappings:**
- **Tactics:** Impact
- **Techniques:** T1498 (Network Denial of Service)

**NIST Controls:**
- SC-5 (Denial of Service Protection)
- IR-4 (Incident Handling)
- CP-2 (Contingency Plan)

**Steps:**
1. **Attack Detection**
   - Traffic analysis
   - Identify attack patterns
   - Determine attack type (volumetric, application-layer)
   - Output: Attack characteristics

2. **Traffic Analysis**
   - Source IP analysis
   - Traffic pattern analysis
   - Bandwidth consumption
   - Output: Analysis report

3. **Mitigation Strategies**
   - Enable DDoS protection (cloud provider)
   - Rate limiting
   - IP blocking
   - Output: Mitigation actions

4. **Service Restoration**
   - Monitor attack status
   - Gradually restore services
   - Verify service health
   - Output: Restoration status

5. **Post-Attack Analysis**
   - Attack timeline
   - Effectiveness of mitigations
   - Improvements needed
   - Output: Analysis report

**Automation Opportunities:**
- Automated DDoS protection activation
- Traffic analysis automation
- Service restoration automation

---

## 8. Insider Threat Response Playbook

**Playbook ID:** `insider-threat-response-v1`

**Description:**
Response procedures for insider threats, including behavioral indicators, access review, and investigation.

**MITRE Mappings:**
- **Tactics:** Collection, Exfiltration
- **Techniques:** T1005 (Data from Local System), T1041 (Exfiltration)

**NIST Controls:**
- PS-3 (Personnel Screening)
- AU-6 (Audit Review)
- IR-4 (Incident Handling)

**Steps:**
1. **Behavioral Indicators**
   - Unusual access patterns
   - Data access anomalies
   - Off-hours activity
   - Output: Indicator list

2. **Access Review**
   - Review user privileges
   - Check data access logs
   - Analyze file transfers
   - Output: Access review report

3. **Data Exfiltration Detection**
   - Check for large data transfers
   - Review external communications
   - Analyze cloud storage usage
   - Output: Exfiltration assessment

4. **Investigation Procedures**
   - Preserve evidence
   - Interview procedures
   - Legal coordination
   - Output: Investigation report

5. **Remediation**
   - Revoke access
   - Disable accounts
   - Data recovery (if possible)
   - Output: Remediation actions

**Automation Opportunities:**
- Behavioral anomaly detection
- Automated access review
- Data exfiltration detection

---

## 9. Cloud Security Incident Playbook

**Playbook ID:** `cloud-security-incident-v1`

**Description:**
Response to cloud security incidents including misconfigurations, unauthorized access, and data exposure.

**MITRE Mappings:**
- **Tactics:** Initial Access, Collection
- **Techniques:** T1078 (Valid Accounts), T1530 (Data from Cloud Storage)

**NIST Controls:**
- AC-3 (Access Enforcement)
- SC-7 (Boundary Protection)
- IR-4 (Incident Handling)

**Steps:**
1. **Misconfiguration Detection**
   - Identify exposed resources
   - Check public access settings
   - Review IAM policies
   - Output: Misconfiguration list

2. **Unauthorized Access**
   - Review access logs
   - Check for privilege escalation
   - Analyze API calls
   - Output: Access analysis

3. **Data Exposure Assessment**
   - Identify exposed data
   - Assess data sensitivity
   - Check for data exfiltration
   - Output: Exposure assessment

4. **IAM Policy Violations**
   - Review policy violations
   - Check for over-privileged accounts
   - Analyze role assignments
   - Output: Violation report

5. **Cloud Provider Coordination**
   - Contact cloud provider support
   - Request logs and forensics
   - Coordinate remediation
   - Output: Coordination status

**Automation Opportunities:**
- Automated misconfiguration detection
- IAM policy analysis
- Cloud log analysis

---

## 10. Supply Chain Attack Response Playbook

**Playbook ID:** `supply-chain-attack-response-v1`

**Description:**
Response to supply chain attacks including compromised dependencies, vendor coordination, and remediation.

**MITRE Mappings:**
- **Tactics:** Initial Access, Persistence
- **Techniques:** T1195 (Supply Chain Compromise), T1574 (Hijack Execution Flow)

**NIST Controls:**
- SA-12 (Supply Chain Protection)
- IR-4 (Incident Handling)
- SI-3 (Malicious Code Protection)

**Steps:**
1. **Compromised Dependency Detection**
   - Identify compromised libraries/packages
   - Check dependency versions
   - Review security advisories
   - Output: Compromised dependencies list

2. **Impact Assessment**
   - Determine affected systems
   - Assess data exposure
   - Check for backdoors
   - Output: Impact assessment

3. **Vendor Coordination**
   - Contact vendor
   - Request security advisory
   - Coordinate patching
   - Output: Vendor coordination status

4. **Remediation Procedures**
   - Update/remove compromised dependencies
   - Verify system integrity
   - Security hardening
   - Output: Remediation status

5. **Prevention Measures**
   - Dependency scanning
   - Software composition analysis
   - Vendor security assessment
   - Output: Prevention actions

**Automation Opportunities:**
- Automated dependency scanning
- Security advisory monitoring
- Automated patching

---

## Playbook Metadata for Vector Database

Each playbook should be stored with the following metadata for optimal RAG retrieval:

```json
{
  "content": "Full playbook text with all steps and procedures",
  "metadata": {
    "playbook_id": "malware-response-v1",
    "name": "Malware Detection & Response",
    "category": "incident_response",
    "keywords": ["malware", "virus", "trojan", "ransomware", "endpoint", "EDR"],
    "mitre_tactics": ["Execution", "Persistence"],
    "mitre_techniques": ["T1059", "T1547"],
    "nist_controls": ["IR-4", "SI-3"],
    "severity": "high",
    "estimated_duration": "2-4 hours",
    "automation_level": "high",
    "last_updated": "2025-11-28"
  }
}
```

---

## Implementation Notes

1. **Vector Embeddings:** Each playbook should be embedded as a whole document, with step-by-step procedures included
2. **Chunking Strategy:** For long playbooks, chunk by major sections (Detection, Containment, Investigation, etc.)
3. **Update Frequency:** Playbooks should be reviewed and updated quarterly
4. **Versioning:** Maintain version history for playbook updates
5. **Customization:** Allow tenant-specific playbook customization while maintaining base templates

---

**Total Playbooks:** 10 standard playbooks ready for vector database storage

