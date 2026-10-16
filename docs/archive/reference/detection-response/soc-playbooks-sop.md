# SOC Playbooks - Standard Operating Procedures

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Last Updated:** December 2, 2025  
**Audience:** SOC Analysts, Security Engineers

---

## Overview

This document describes the standard operating procedures for responding to the 10 automated detection alerts in SentinelGrid, aligned with NIST SP 800-61 Incident Response phases.

---

## Detection Alert Response Matrix

| Alert Type | Severity | Auto-Execute | Analyst Action Required | Target MTTR |
|------------|----------|--------------|------------------------|-------------|
| Suspicious Login | High | ❌ | Review, approve containment | 15 min |
| User-Reported Phishing | Medium | ✅ | Review classification | 30 min |
| Email Campaign | High | ✅ | Monitor bulk removal | 15 min |
| Endpoint Malware | High | ✅ | Verify quarantine | 10 min |
| Ransomware | Critical | ✅ | Immediate isolation | 5 min |
| Public Cloud Storage | High | ✅ | Verify remediation | 30 min |
| Privilege Escalation | High | ❌ | Validate legitimacy | 20 min |
| Password Spray | Medium | ✅ | Block IP, monitor | 30 min |
| Data Exfiltration | High | ❌ | Investigate, contain | 15 min |
| Lost Device | Medium | ✅ | Coordinate with user | 60 min |

---

## SOP 1: Suspicious Login / Account Takeover (SG-DET-001)

### Detection Criteria
- ≥5 failed login attempts from same IP + user
- Followed by 1 successful login
- Timeframe: 10 minutes

### Automatic Actions (Playbook)
- ❌ **None** - Requires analyst review

### Analyst Response (NIST Phases)

#### Detection & Analysis (5 minutes)
1. **Review alert details:**
   - Source IP and geolocation
   - User account affected
   - Time of failures vs. success
   - Device/browser information

2. **Validate legitimacy:**
   - Contact user (via Slack/Teams/phone)
   - Check if travel is expected
   - Review recent account activity

3. **Decision:**
   - **Legitimate:** Close incident as false positive
   - **Suspicious:** Proceed to containment

#### Containment (5 minutes)
1. **Disable account temporarily**
2. **Terminate all active sessions**
3. **Force password reset**
4. **Enable MFA if not configured**

#### Eradication & Recovery (5 minutes)
1. **Verify no unauthorized access**
2. **Check for data exfiltration**
3. **Enable account after password reset**
4. **Confirm user can log in successfully**

#### Post-Incident
1. **Document incident report**
2. **Update security awareness training**
3. **Consider additional MFA enforcement**

**Target MTTR:** 15 minutes (Detection to Resolution)

---

## SOP 2: User-Reported Phishing (SG-DET-002)

### Detection Criteria
- User forwards email to phishing@company
- Or clicks "Report Phishing" button

### Automatic Actions (Playbook)
- ✅ **Email ingestion** - Extract headers, body, URLs, attachments
- ✅ **AI classification** - Classify as benign/spam/phishing/spearphishing
- ✅ **Search mailboxes** - Find similar emails
- ⏸️  **Removal pending** - Awaits analyst confirmation

### Analyst Response

#### Detection & Analysis (10 minutes)
1. **Review AI classification** (confidence %, reasoning)
2. **Inspect email:**
   - Sender domain reputation
   - URL destinations (typosquatting?)
   - Attachments (if any)
   - Email headers (SPF, DKIM, DMARC)

3. **Decision:**
   - **Benign:** Close, thank user
   - **Phishing:** Proceed to containment

#### Containment (15 minutes)
1. **Approve bulk removal** from all mailboxes
2. **Block sender domain** at email gateway
3. **Block malicious URLs** at web proxy
4. **Add IOCs to threat intelligence**

#### Post-Incident (5 minutes)
1. **Thank reporting user**
2. **Send awareness note** to potentially affected users
3. **Update email filters**

**Target MTTR:** 30 minutes

---

## SOP 3: Ransomware Detection (SG-DET-005) ⚠️ CRITICAL

### Detection Criteria
- Ransomware family detected by EDR/AV
- OR: Behavioral pattern (mass file encryption)

### Automatic Actions (Playbook)
- ✅ **Immediate host isolation** - Network disconnection
- ✅ **Process termination** - Kill ransomware process
- ✅ **Snapshot creation** - For forensics
- ✅ **Backup verification** - Check backup integrity
- ✅ **Alert escalation** - Page on-call engineer

### Analyst Response

#### Containment (IMMEDIATE - 2 minutes)
1. **Verify isolation** - Confirm host cannot reach network
2. **Check lateral movement** - Search for infection on other hosts
3. **Isolate additional hosts** if needed
4. **Preserve evidence** - Memory dump, disk image

#### Eradication (30 minutes)
1. **Identify ransomware variant** (family, version)
2. **Check for decryption tools** (NoMoreRansom.org)
3. **Wipe and rebuild** affected hosts
4. **Patch vulnerabilities** exploited for entry

#### Recovery (Variable)
1. **Restore from backup** (verify backup is clean)
2. **Verify file integrity**
3. **Test system functionality**
4. **Monitor for re-infection** (48 hours)

#### Post-Incident
1. **Root cause analysis**
2. **Update detection rules**
3. **Enhance backup procedures**
4. **Executive report**

**Target MTTR:** 2 hours (Containment to Recovery)

---

## SOP 4: Password Spray Detection (SG-DET-008)

### Detection Criteria
- ≥50 failed login attempts from single IP
- Against ≥10 different user accounts
- Timeframe: 10 minutes

### Automatic Actions (Playbook)
- ✅ **Block source IP** at firewall
- ✅ **Add to threat feed**
- ✅ **Alert affected users**

### Analyst Response

#### Detection & Analysis (5 minutes)
1. **Review attack pattern:**
   - Source IP and geolocation
   - List of targeted usernames
   - Time distribution
   - Any successful logins?

2. **Check IP reputation** (AbuseIPDB, etc.)

#### Containment (10 minutes)
1. **Verify IP block** effective
2. **If any successes:** Force password reset for those accounts
3. **Review firewall logs** for additional attacker IPs
4. **Block entire IP range** if part of botnet

#### Post-Incident (15 minutes)
1. **Document attack** (IP, usernames, timeframe)
2. **Update WAF rules** if web-based
3. **Consider geofencing** if country-based
4. **User awareness** if credentials may be compromised

**Target MTTR:** 30 minutes

---

## SOP 5: Data Exfiltration (SG-DET-009)

### Detection Criteria
- User transfers >10GB in 1 hour
- To external destinations

### Automatic Actions (Playbook)
- ❌ **None** - High false positive risk

### Analyst Response

#### Detection & Analysis (10 minutes)
1. **Review transfer details:**
   - User identity and department
   - Destination IPs/domains
   - Data volume and timing
   - File types (if available)

2. **Check legitimacy:**
   - Contact user's manager
   - Review approved business purpose
   - Check for remote work, cloud backup

3. **Decision:**
   - **Legitimate:** Whitelist, document exception
   - **Suspicious:** Proceed to containment

#### Containment (5 minutes)
1. **Disable user account**
2. **Block destination IPs**
3. **Terminate active sessions**
4. **Preserve logs** for forensics

#### Investigation (30-60 minutes)
1. **Identify what data** was transferred
2. **Check data classification** (PII, PCI, PHI?)
3. **Review user's recent activity**
4. **Check endpoint for malware**
5. **Interview user**

#### Eradication & Recovery
1. **Remove malware** (if present)
2. **Reset credentials**
3. **Review access permissions**
4. **Enable account** after verification

#### Post-Incident
1. **Data breach notification** (if required by law)
2. **Legal/compliance coordination**
3. **Update DLP policies**
4. **Executive report**

**Target MTTR:** 60 minutes (Containment), 4 hours (Full investigation)

---

## Escalation Matrix

| Scenario | Escalate To | Timeframe |
|----------|-------------|-----------|
| Ransomware | On-call Engineer, CISO | Immediate |
| Data exfil >100GB | SOC Manager, Legal | 15 minutes |
| Exec account compromise | SOC Manager, CIO | 10 minutes |
| Mass phishing campaign | SOC Manager | 30 minutes |
| Public data exposure | CISO, Legal | 30 minutes |
| Standard alerts | SOC Tier 2 | 60 minutes |

---

## NIST Phase Tracking

All incidents follow NIST SP 800-61 phases:

1. **Detection & Analysis** (Status: NEW, TRIAGED, INVESTIGATING)
2. **Containment** (Status: CONTAINED, ISOLATED)
3. **Eradication** (Status: ERADICATING, ERADICATED)
4. **Recovery** (Status: RECOVERING, RECOVERED)
5. **Post-Incident** (Status: LESSONS_LEARNED, CLOSED)

**SentinelGrid automatically tracks phase progression in incident_timeline table.**

---

## Playbook Execution

### Auto-Execute Playbooks
These run without approval:
- User-Reported Phishing
- Email Campaign
- Endpoint Malware
- Ransomware (CRITICAL)
- Public Cloud Storage
- Password Spray
- Lost Device

### Manual Approval Required
These need analyst review:
- Suspicious Login (potential false positive)
- Privilege Escalation (may be legitimate)
- Data Exfiltration (high false positive rate)

**To approve playbook:**
1. Review incident details
2. Click "Approve Playbook Execution"
3. Monitor playbook progress

---

## Documentation Requirements

For NIST compliance, every incident must have:

- [x] **Detection:** How was it detected? (auto via monitor)
- [x] **Timeline:** Complete chronological log (auto in incident_timeline)
- [x] **Actions:** What actions were taken? (auto in incident_actions)
- [x] **Observables:** What IOCs were identified? (auto in incident_observables)
- [ ] **Root Cause:** Why did it happen? (analyst documents)
- [ ] **Lessons Learned:** How to prevent? (analyst documents)
- [ ] **Final Report:** Executive summary (analyst documents)

**Automatic fields** are populated by the system.  
**Analyst fields** must be completed before closing incident.

---

## Key Performance Indicators (KPIs)

### SOC Team KPIs
- Mean Time to Acknowledge (MTTA) < 10 minutes
- Mean Time to Respond (MTTR) < 30 minutes
- False Positive Rate < 5%
- Playbook Adoption Rate > 80%

### Detection System KPIs
- Monitor Uptime > 99.5%
- Webhook Success Rate > 99%
- Incident Creation Time < 2 seconds
- Traceability Coverage = 100%

---

## Training Checklist

New SOC analysts must complete:

- [ ] Review this SOP document
- [ ] Complete detection alert walkthroughs (all 10 types)
- [ ] Practice incident response in lab environment
- [ ] Shadow senior analyst for 1 week
- [ ] Handle supervised incidents for 2 weeks
- [ ] Pass certification quiz (80% minimum)

---

**Document Owner:** SOC Manager  
**Review Cycle:** Quarterly  
**Next Review:** March 2, 2026
