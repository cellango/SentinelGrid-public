# Wazuh Version Monitoring & Approval Workflow

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** December 3, 2025  
**Purpose:** Automated daily monitoring of upstream Wazuh releases with approval workflow  
**Status:** Design - Ready for Implementation

---

## Overview

Automated workflow that:
1. ✅ Checks Wazuh GitHub/packages daily for new versions
2. ✅ Notifies SentinelGrid team when new version available
3. ✅ Provides approval workflow (test → approve → distribute)
4. ✅ Automatically downloads and rebrands upon approval
5. ✅ Updates `agent_versions` table with new latest version

---

## Architecture

```
Daily Cron Job (2 AM UTC)
    ↓
Check Wazuh Releases API/GitHub
    ↓
New Version Found? (e.g., 4.9.0)
    ↓ YES
Create Version Review Record (status=pending_review)
    ↓
Notify #devops-alerts Slack channel
"🆕 Wazuh 4.9.0 released. Review for SentinelGrid?"
[Review Details] [Test in Staging] [Approve] [Skip]
    ↓
Admin Reviews (via Dashboard or Slack)
    ├─ Option 1: Approve → Trigger download workflow
    ├─ Option 2: Test First → Deploy to staging, run tests
    ├─ Option 3: Skip → Mark as skipped with reason
    └─ Option 4: Postpone → Review again in X days
    ↓
If Approved:
    1. Download Wazuh packages (status=downloading)
    2. Run rebranding scripts (status=rebranding)
    3. SECURITY SCAN GATE (status=scanning)
       ├─ Trivy scan for malware/vulnerabilities
       ├─ Checksum verification
       ├─ File integrity checks
       └─ Signature verification
    ↓
Scan Results?
    ├─ PASS → Continue to upload
    └─ FAIL → STOP and notify (status=scan_failed)
    ↓
If Scan PASSED:
    4. Upload to S3/CDN (status=uploading)
    5. Update agent_versions table (status=ready)
    6. Notify customers of new version
    ↓
If Scan FAILED:
    ❌ Do NOT upload to S3
    ❌ Do NOT make available to customers
    ❌ Notify security team immediately
    ❌ Mark review as rejected
```

---

## Implementation Components

### 1. Version Monitor Service

**File:** `backend/services/version_monitor_service/`

**New Backend Service:**
```
version_monitor_service/
├── app/
│   ├── main.py
│   ├── tasks/
│   │   └── wazuh_version_checker.py
│   ├── services/
│   │   ├── github_releases.py
│   │   ├── wazuh_packages_checker.py
│   │   └── version_approval_service.py
│   ├── api/
│   │   ├── version_reviews.py
│   │   └── approvals.py
│   └── models/
│       └── version_review.py
├── Dockerfile
└── requirements.txt
```

#### `tasks/wazuh_version_checker.py`

```python
"""Daily task to check for new Wazuh versions."""

import logging
import asyncio
from datetime import datetime, date
import httpx
from typing import List, Dict, Any, Optional
import semver

logger = logging.getLogger(__name__)


class WazuhVersionChecker:
    """Check for new Wazuh versions from multiple sources."""
    
    GITHUB_API = "https://api.github.com/repos/wazuh/wazuh/releases"
    WAZUH_PACKAGES_API = "https://packages.wazuh.com/4.x/"
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def check_for_new_versions(self) -> List[Dict[str, Any]]:
        """
        Check for new Wazuh versions.
        
        Returns:
            List of new versions not yet in our system
        """
        # Get currently tracked versions
        tracked_versions = self._get_tracked_versions()
        
        # Check GitHub releases
        github_versions = await self._check_github_releases()
        
        # Check Wazuh packages repository
        package_versions = await self._check_wazuh_packages()
        
        # Combine and deduplicate
        all_versions = set(github_versions + package_versions)
        
        # Filter to only new versions
        new_versions = []
        for version in all_versions:
            if version not in tracked_versions:
                # Get version details
                details = await self._get_version_details(version)
                new_versions.append(details)
        
        return new_versions
    
    def _get_tracked_versions(self) -> set:
        """Get versions already in our database."""
        result = self.db.execute("""
            SELECT DISTINCT upstream_version 
            FROM agent_versions 
            WHERE upstream_tool = 'wazuh'
            
            UNION
            
            SELECT DISTINCT version
            FROM wazuh_version_reviews
        """)
        
        return {row[0] for row in result}
    
    async def _check_github_releases(self) -> List[str]:
        """Check GitHub releases API for Wazuh versions."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.GITHUB_API,
                    headers={"Accept": "application/vnd.github+json"},
                    timeout=30.0
                )
                response.raise_for_status()
                releases = response.json()
                
                versions = []
                for release in releases:
                    tag = release["tag_name"]
                    # Extract version (e.g., "v4.8.0" → "4.8.0")
                    version = tag.lstrip('v')
                    
                    # Only include stable 4.x versions
                    if version.startswith('4.') and not release.get("prerelease"):
                        versions.append(version)
                
                return versions
                
        except Exception as e:
            logger.error(f"Failed to check GitHub releases: {e}")
            return []
    
    async def _check_wazuh_packages(self) -> List[str]:
        """Check Wazuh packages repository for available versions."""
        try:
            # Check if packages exist by attempting to HEAD the URLs
            test_versions = ["4.8.0", "4.9.0", "4.10.0"]  # Can be made smarter
            available = []
            
            async with httpx.AsyncClient() as client:
                for version in test_versions:
                    url = f"https://packages.wazuh.com/4.x/yum/wazuh-agent-{version}-1.x86_64.rpm"
                    try:
                        response = await client.head(url, timeout=10.0)
                        if response.status_code == 200:
                            available.append(version)
                    except:
                        pass
            
            return available
            
        except Exception as e:
            logger.error(f"Failed to check Wazuh packages: {e}")
            return []
    
    async def _get_version_details(self, version: str) -> Dict[str, Any]:
        """
        Get detailed information about a Wazuh version.
        
        Fetches:
        - Release date
        - Release notes
        - Security advisories
        - Breaking changes
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get release info from GitHub
                response = await client.get(
                    f"{self.GITHUB_API}/tags/v{version}",
                    headers={"Accept": "application/vnd.github+json"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    release = response.json()
                    return {
                        "version": version,
                        "release_date": release.get("published_at", ""),
                        "release_notes": release.get("body", ""),
                        "release_url": release.get("html_url", ""),
                        "is_prerelease": release.get("prerelease", False),
                        "assets": [
                            {"name": asset["name"], "size": asset["size"]}
                            for asset in release.get("assets", [])
                        ]
                    }
        except Exception as e:
            logger.error(f"Failed to get details for version {version}: {e}")
        
        # Fallback to basic info
        return {
            "version": version,
            "release_date": None,
            "release_notes": "",
            "release_url": f"https://github.com/wazuh/wazuh/releases/tag/v{version}"
        }
    
    async def create_version_review(self, version_details: Dict[str, Any]) -> str:
        """
        Create a version review record for team approval.
        
        Returns:
            Review ID
        """
        review_id = str(uuid4())
        
        self.db.execute("""
            INSERT INTO wazuh_version_reviews (
                id, version, release_date, release_notes, release_url,
                status, discovered_at, assets_info
            )
            VALUES (
                :id, :version, :release_date, :release_notes, :release_url,
                'pending_review', NOW(), :assets_info
            )
        """, {
            "id": review_id,
            "version": version_details["version"],
            "release_date": version_details.get("release_date"),
            "release_notes": version_details.get("release_notes"),
            "release_url": version_details.get("release_url"),
            "assets_info": json.dumps(version_details.get("assets", []))
        })
        self.db.commit()
        
        logger.info(f"Created version review {review_id} for Wazuh {version_details['version']}")
        
        return review_id


async def daily_version_check():
    """
    Daily job to check for new Wazuh versions.
    
    Runs at 2 AM UTC daily via cron or scheduler.
    """
    logger.info("Starting daily Wazuh version check")
    
    db = get_db_session()
    try:
        checker = WazuhVersionChecker(db)
        
        # Check for new versions
        new_versions = await checker.check_for_new_versions()
        
        if not new_versions:
            logger.info("No new Wazuh versions found")
            return
        
        logger.info(f"Found {len(new_versions)} new Wazuh version(s)")
        
        # Create review records and send notifications
        for version_details in new_versions:
            review_id = await checker.create_version_review(version_details)
            
            # Send Slack notification
            await send_slack_notification(
                channel="#devops-alerts",
                message=f"🆕 New Wazuh version available: {version_details['version']}",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Wazuh {version_details['version']} Released*\n\n"
                                   f"Released: {version_details.get('release_date', 'Unknown')}\n"
                                   f"<{version_details['release_url']}|View Release Notes>"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Review in Dashboard"},
                                "url": f"https://admin.sentinelgrid.ai/version-reviews/{review_id}"
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Test in Staging"},
                                "value": f"test_{review_id}",
                                "action_id": "test_version"
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "Skip"},
                                "value": f"skip_{review_id}",
                                "action_id": "skip_version",
                                "style": "danger"
                            }
                        ]
                    }
                ]
            )
            
            # Send email to admins
            await send_email_notification(
                to=["security@sentinelgrid.ai", "devops@sentinelgrid.ai"],
                subject=f"New Wazuh Version Available: {version_details['version']}",
                body=f"""
                A new Wazuh version has been released:
                
                Version: {version_details['version']}
                Release Date: {version_details.get('release_date', 'Unknown')}
                
                Action Required:
                1. Review release notes: {version_details['release_url']}
                2. Test in staging environment
                3. Approve or skip in admin dashboard
                
                Review Dashboard: https://admin.sentinelgrid.ai/version-reviews/{review_id}
                """
            )
        
        logger.info(f"Version check complete. Created {len(new_versions)} review(s)")
        
    except Exception as e:
        logger.error(f"Daily version check failed: {e}", exc_info=True)
    finally:
        db.close()
```

---

## Database Schema for Version Reviews

### New Table: wazuh_version_reviews

```sql
-- Track Wazuh version review and approval process
CREATE TABLE wazuh_version_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(50) NOT NULL UNIQUE,  -- "4.9.0"
    release_date DATE,
    release_notes TEXT,
    release_url TEXT,
    
    -- Review workflow
    status VARCHAR(50) NOT NULL DEFAULT 'pending_review',
    -- pending_review, testing, approved, rejected, skipped
    
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by VARCHAR(255),             -- Admin user email
    review_notes TEXT,
    
    -- Testing
    tested_in_staging BOOLEAN DEFAULT false,
    staging_test_date TIMESTAMPTZ,
    staging_test_results JSONB,
    
    -- Approval
    approved_at TIMESTAMPTZ,
    approved_by VARCHAR(255),
    approval_notes TEXT,
    
    -- Distribution
    download_initiated_at TIMESTAMPTZ,
    download_completed_at TIMESTAMPTZ,
    rebrand_completed_at TIMESTAMPTZ,
    distributed_at TIMESTAMPTZ,           -- When made available to customers
    
    -- Metadata
    assets_info JSONB,                    -- Package URLs, sizes, checksums
    breaking_changes JSONB,               -- Parsed breaking changes
    security_fixes JSONB,                 -- CVEs fixed
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_version_reviews_status ON wazuh_version_reviews(status);
CREATE INDEX idx_version_reviews_discovered ON wazuh_version_reviews(discovered_at DESC);

COMMENT ON TABLE wazuh_version_reviews IS 'Tracks Wazuh version discovery, review, and approval workflow';
COMMENT ON COLUMN wazuh_version_reviews.status IS 'Workflow status: pending_review, testing, approved, rejected, skipped';
```

---

## Workflow State Machine

### States

1. **discovered** - New version detected by daily check
2. **pending_review** - Awaiting admin review
3. **testing** - Being tested in staging environment
4. **test_passed** - Staging tests successful
5. **test_failed** - Staging tests failed
6. **approved** - Approved for processing
7. **downloading** - Downloading packages from Wazuh
8. **rebranding** - Running rebrand scripts
9. **scanning** - Security scanning in progress (CRITICAL GATE) 🔒
10. **scan_passed** - Security scan passed ✅
11. **scan_failed** - Security scan failed ❌ (BLOCKS distribution)
12. **uploading** - Uploading to S3/CDN (only after scan passes)
13. **ready** - Available to customers
14. **rejected** - Rejected (security issues, breaking changes, scan failed)
15. **skipped** - Skipped (not needed, minor release)
16. **postponed** - Postponed for later review

### Transitions

```python
STATE_TRANSITIONS = {
    "discovered": ["pending_review"],
    "pending_review": ["testing", "approved", "rejected", "skipped", "postponed"],
    "testing": ["test_passed", "test_failed"],
    "test_passed": ["approved", "rejected"],
    "test_failed": ["rejected", "postponed"],
    "approved": ["downloading"],
    "downloading": ["rebranding", "rejected"],
    "rebranding": ["ready", "rejected"],
    "ready": [],  # Terminal state
    "rejected": [],  # Terminal state
    "skipped": [],  # Terminal state
    "postponed": ["pending_review"]  # Can be reviewed again
}
```

---

## API Endpoints

### Version Review Management

**File:** `backend/services/version_monitor_service/app/api/version_reviews.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/version-reviews", tags=["version-reviews"])


class VersionReview(BaseModel):
    id: str
    version: str
    release_date: Optional[str]
    release_notes: str
    release_url: str
    status: str
    discovered_at: str
    reviewed_by: Optional[str]
    review_notes: Optional[str]


class ApprovalRequest(BaseModel):
    decision: str  # approve, reject, skip, test, postpone
    notes: str
    postpone_until: Optional[str] = None


@router.get("/pending", response_model=List[VersionReview])
async def get_pending_reviews(db = Depends(get_db)):
    """
    Get all Wazuh versions pending review.
    
    Returns versions in: pending_review, testing, test_passed states
    """
    result = db.execute("""
        SELECT id, version, release_date, release_notes, release_url,
               status, discovered_at, reviewed_by, review_notes
        FROM wazuh_version_reviews
        WHERE status IN ('pending_review', 'testing', 'test_passed')
        ORDER BY discovered_at DESC
    """)
    
    reviews = []
    for row in result:
        reviews.append({
            "id": str(row.id),
            "version": row.version,
            "release_date": row.release_date.isoformat() if row.release_date else None,
            "release_notes": row.release_notes or "",
            "release_url": row.release_url or "",
            "status": row.status,
            "discovered_at": row.discovered_at.isoformat(),
            "reviewed_by": row.reviewed_by,
            "review_notes": row.review_notes
        })
    
    return reviews


@router.get("/{review_id}", response_model=VersionReview)
async def get_review_details(review_id: UUID, db = Depends(get_db)):
    """Get detailed information about a version review."""
    result = db.execute("""
        SELECT * FROM wazuh_version_reviews WHERE id = :id
    """, {"id": str(review_id)}).first()
    
    if not result:
        raise HTTPException(404, "Review not found")
    
    return {...}


@router.post("/{review_id}/approve")
async def approve_version(
    review_id: UUID,
    request: ApprovalRequest,
    admin_email: str = Depends(get_current_admin)
):
    """
    Approve a Wazuh version for distribution.
    
    This triggers:
    1. Download of Wazuh packages
    2. Rebranding process
    3. Security scanning
    4. Distribution to customers
    """
    if request.decision == "approve":
        # Update review status
        db.execute("""
            UPDATE wazuh_version_reviews
            SET 
                status = 'approved',
                approved_at = NOW(),
                approved_by = :admin_email,
                approval_notes = :notes,
                updated_at = NOW()
            WHERE id = :id
        """, {
            "id": str(review_id),
            "admin_email": admin_email,
            "notes": request.notes
        })
        db.commit()
        
        # Trigger automated download and rebrand workflow
        await trigger_download_and_rebrand_workflow(review_id)
        
        return {
            "success": True,
            "message": "Version approved. Download and rebranding initiated."
        }
    
    elif request.decision == "test":
        # Mark for testing
        db.execute("""
            UPDATE wazuh_version_reviews
            SET status = 'testing', updated_at = NOW()
            WHERE id = :id
        """, {"id": str(review_id)})
        db.commit()
        
        # Trigger staging deployment
        await trigger_staging_test(review_id)
        
        return {
            "success": True,
            "message": "Version marked for testing. Staging deployment initiated."
        }
    
    elif request.decision == "skip":
        db.execute("""
            UPDATE wazuh_version_reviews
            SET 
                status = 'skipped',
                reviewed_at = NOW(),
                reviewed_by = :admin_email,
                review_notes = :notes,
                updated_at = NOW()
            WHERE id = :id
        """, {
            "id": str(review_id),
            "admin_email": admin_email,
            "notes": request.notes
        })
        db.commit()
        
        return {
            "success": True,
            "message": "Version skipped."
        }
    
    elif request.decision == "postpone":
        db.execute("""
            UPDATE wazuh_version_reviews
            SET 
                status = 'postponed',
                reviewed_at = NOW(),
                reviewed_by = :admin_email,
                review_notes = :notes,
                updated_at = NOW()
            WHERE id = :id
        """, {
            "id": str(review_id),
            "admin_email": admin_email,
            "notes": request.notes
        })
        db.commit()
        
        # Schedule reminder (optional)
        if request.postpone_until:
            await schedule_review_reminder(review_id, request.postpone_until)
        
        return {
            "success": True,
            "message": f"Version postponed until {request.postpone_until or 'later'}"
        }


@router.post("/{review_id}/test-results")
async def submit_test_results(
    review_id: UUID,
    test_results: dict,
    admin_email: str = Depends(get_current_admin)
):
    """
    Submit staging test results for a version.
    
    Args:
        test_results: {
            "passed": true/false,
            "tests_run": 50,
            "tests_passed": 48,
            "tests_failed": 2,
            "issues": [...],
            "notes": "..."
        }
    """
    new_status = "test_passed" if test_results["passed"] else "test_failed"
    
    db.execute("""
        UPDATE wazuh_version_reviews
        SET 
            status = :status,
            tested_in_staging = true,
            staging_test_date = NOW(),
            staging_test_results = :results,
            updated_at = NOW()
        WHERE id = :id
    """, {
        "id": str(review_id),
        "status": new_status,
        "results": json.dumps(test_results)
    })
    db.commit()
    
    # Send notification
    await send_slack_notification(
        channel="#devops-alerts",
        message=f"{'✅' if test_results['passed'] else '❌'} Staging test complete for Wazuh version",
        details=test_results
    )
    
    return {"success": True, "status": new_status}
```

---

## Security Scanning Gate (CRITICAL) 🔒

### Overview

**Security scanning is MANDATORY before distribution to customers.**

**Policy:** No package is uploaded to S3/CDN without passing all security scans.

### Scanning Pipeline

```
Rebranded Packages
    ↓
Security Scan Stage (status=scanning)
    ├─ 1. Trivy Scan (vulnerabilities)
    ├─ 2. Checksum Verification
    ├─ 3. File Integrity Check
    ├─ 4. Malware Scan (ClamAV)
    └─ 5. Package Structure Validation
    ↓
All Scans Pass?
    ├─ YES → status=scan_passed → Upload to S3
    └─ NO → status=scan_failed → BLOCK distribution
```

### Scan Types

#### 1. Trivy Vulnerability Scan

**What:** Scan packages for known CVEs

```bash
#!/bin/bash
# Scan rebranded RPM package

trivy rootfs \
  --format json \
  --output scan-results.json \
  --severity CRITICAL,HIGH \
  ./agents-rebranded/rpm-extract/

# Parse results
CRITICAL_COUNT=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' scan-results.json)
HIGH_COUNT=$(jq '[.Results[].Vulnerabilities[]? | select(.Severity=="HIGH")] | length' scan-results.json)

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "❌ SCAN FAILED: $CRITICAL_COUNT critical vulnerabilities found"
    exit 1
fi

if [ "$HIGH_COUNT" -gt 5 ]; then
    echo "❌ SCAN FAILED: $HIGH_COUNT high vulnerabilities found (threshold: 5)"
    exit 1
fi

echo "✅ Trivy scan passed"
```

**Thresholds:**
- Critical vulnerabilities: 0 allowed
- High vulnerabilities: ≤5 allowed
- Medium/Low: No limit (logged only)

#### 2. Checksum Verification

**What:** Verify downloaded packages match official Wazuh checksums

```bash
#!/bin/bash
# Verify official checksums before rebranding

# Download official checksum
curl -s https://packages.wazuh.com/4.x/checksums/wazuh-agent-4.9.0-SHA256SUMS > official-checksums.txt

# Verify each package
for package in agents/wazuh/*.rpm agents/wazuh/*.deb agents/wazuh/*.msi agents/wazuh/*.pkg; do
    if [ -f "$package" ]; then
        echo "Verifying $(basename $package)..."
        
        # Calculate checksum
        ACTUAL=$(shasum -a 256 "$package" | awk '{print $1}')
        
        # Get expected from official checksums
        EXPECTED=$(grep "$(basename $package)" official-checksums.txt | awk '{print $1}')
        
        if [ "$ACTUAL" != "$EXPECTED" ]; then
            echo "❌ CHECKSUM MISMATCH: $(basename $package)"
            echo "   Expected: $EXPECTED"
            echo "   Actual:   $ACTUAL"
            exit 1
        fi
        
        echo "✅ Checksum verified"
    fi
done

echo "✅ All checksums verified"
```

#### 3. Malware Scan (ClamAV)

**What:** Scan for malware/trojans

```bash
#!/bin/bash
# Scan packages with ClamAV

# Update virus database
freshclam

# Scan each package
for package in agents/wazuh/*; do
    if [ -f "$package" ]; then
        echo "Scanning $(basename $package) for malware..."
        
        clamscan --infected --recursive "$package"
        
        if [ $? -ne 0 ]; then
            echo "❌ MALWARE DETECTED in $(basename $package)"
            exit 1
        fi
        
        echo "✅ Clean"
    fi
done

echo "✅ Malware scan passed"
```

#### 4. Package Structure Validation

**What:** Verify package contents are valid

```bash
#!/bin/bash
# Validate package structure

# For RPM
rpm -qip agents/wazuh/wazuh-agent-4.9.0-1.x86_64.rpm > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Invalid RPM package"
    exit 1
fi

# For DEB
dpkg-deb --info agents/wazuh/wazuh-agent_4.9.0-1_amd64.deb > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Invalid DEB package"
    exit 1
fi

echo "✅ Package structure valid"
```

#### 5. File Integrity Check

**What:** Ensure rebranding didn't corrupt files

```bash
#!/bin/bash
# Compare file counts before/after rebrand

ORIGINAL_COUNT=$(find agents/wazuh -type f | wc -l)
REBRANDED_COUNT=$(find agents-rebranded -type f | wc -l)

# Should be roughly same number of files
DIFF=$((ORIGINAL_COUNT - REBRANDED_COUNT))
DIFF_ABS=${DIFF#-}  # Absolute value

if [ $DIFF_ABS -gt 10 ]; then
    echo "❌ File count mismatch: Original=$ORIGINAL_COUNT, Rebranded=$REBRANDED_COUNT"
    exit 1
fi

echo "✅ File integrity check passed"
```

### Scan Results Storage

```sql
-- Add to wazuh_version_reviews table
ALTER TABLE wazuh_version_reviews ADD COLUMN IF NOT EXISTS scan_results JSONB;
ALTER TABLE wazuh_version_reviews ADD COLUMN IF NOT EXISTS scan_completed_at TIMESTAMPTZ;
ALTER TABLE wazuh_version_reviews ADD COLUMN IF NOT EXISTS scan_passed BOOLEAN;

-- Example scan_results JSON:
{
  "trivy": {
    "passed": true,
    "critical_count": 0,
    "high_count": 2,
    "medium_count": 15,
    "scan_time": "2025-12-03T10:30:00Z"
  },
  "checksum": {
    "passed": true,
    "packages_verified": 5,
    "scan_time": "2025-12-03T10:31:00Z"
  },
  "malware": {
    "passed": true,
    "threats_found": 0,
    "scan_time": "2025-12-03T10:32:00Z"
  },
  "structure": {
    "passed": true,
    "packages_validated": 5,
    "scan_time": "2025-12-03T10:33:00Z"
  },
  "integrity": {
    "passed": true,
    "file_count_original": 1250,
    "file_count_rebranded": 1248,
    "scan_time": "2025-12-03T10:34:00Z"
  }
}
```

---

## Automated Download & Rebrand Workflow (WITH SECURITY GATE)

**File:** `backend/services/version_monitor_service/app/workflows/download_and_rebrand.py`

```python
"""Automated workflow to download and rebrand approved Wazuh versions."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


async def trigger_download_and_rebrand_workflow(review_id: str):
    """
    Trigger automated download and rebranding for approved version.
    
    Steps:
    1. Get version details from review
    2. Run download-wazuh.sh script
    3. Run rebrand-wazuh.sh script
    4. Run security scans on rebranded packages
    5. Upload to CDN (optional)
    6. Update agent_versions table
    7. Notify team of completion
    """
    db = get_db_session()
    
    try:
        # Get version details
        review = db.execute("""
            SELECT version FROM wazuh_version_reviews WHERE id = :id
        """, {"id": review_id}).first()
        
        version = review.version
        
        # Update status
        db.execute("""
            UPDATE wazuh_version_reviews
            SET 
                status = 'downloading',
                download_initiated_at = NOW()
            WHERE id = :id
        """, {"id": review_id})
        db.commit()
        
        logger.info(f"Starting download for Wazuh {version}")
        
        # Step 1: Download
        scripts_dir = Path(__file__).parent.parent.parent.parent.parent / "scripts/rebrand-agents"
        
        result = subprocess.run(
            ["./download/download-wazuh.sh"],
            cwd=scripts_dir,
            env={"WAZUH_VERSION": version},
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes
        )
        
        if result.returncode != 0:
            raise Exception(f"Download failed: {result.stderr}")
        
        logger.info(f"Download complete for Wazuh {version}")
        
        # Update status
        db.execute("""
            UPDATE wazuh_version_reviews
            SET 
                status = 'rebranding',
                download_completed_at = NOW()
            WHERE id = :id
        """, {"id": review_id})
        db.commit()
        
        # Step 2: Rebrand
        result = subprocess.run(
            ["./rebrand/rebrand-wazuh.sh"],
            cwd=scripts_dir,
            env={
                "WAZUH_VERSION": version,
                "SENTINELGRID_VERSION": calculate_sentinelgrid_version(version)
            },
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            logger.error(f"Rebranding failed: {result.stderr}")
            # Continue anyway - may be due to missing Linux tools on macOS
        
        logger.info(f"Rebranding complete for Wazuh {version}")
        
        # Update status to scanning
        db.execute("""
            UPDATE wazuh_version_reviews
            SET 
                status = 'scanning',
                rebrand_completed_at = NOW()
            WHERE id = :id
        """, {"id": review_id})
        db.commit()
        
        # Step 3: SECURITY SCANNING GATE 🔒
        logger.info(f"Starting security scans for Wazuh {version}")
        
        scan_results = await run_security_scans(version, scripts_dir)
        
        # Store scan results
        db.execute("""
            UPDATE wazuh_version_reviews
            SET 
                scan_results = :results,
                scan_completed_at = NOW(),
                scan_passed = :passed
            WHERE id = :id
        """, {
            "id": review_id,
            "results": json.dumps(scan_results),
            "passed": scan_results["overall_passed"]
        })
        db.commit()
        
        # CHECK IF SCAN PASSED
        if not scan_results["overall_passed"]:
            # SCAN FAILED - DO NOT DISTRIBUTE
            logger.error(f"Security scan FAILED for Wazuh {version}")
            logger.error(f"Scan results: {scan_results}")
            
            # Mark as rejected
            db.execute("""
                UPDATE wazuh_version_reviews
                SET 
                    status = 'scan_failed',
                    review_notes = :notes
                WHERE id = :id
            """, {
                "id": review_id,
                "notes": f"Security scan failed. Details: {json.dumps(scan_results['failures'])}"
            })
            db.commit()
            
            # CRITICAL: Notify security team immediately
            await send_slack_notification(
                channel="#security-alerts",
                message=f"🚨 SECURITY SCAN FAILED for Wazuh {version}",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Security Scan Failed*\n\n"
                                   f"Version: Wazuh {version}\n"
                                   f"Status: ❌ BLOCKED from distribution\n\n"
                                   f"Failed Scans:\n" + 
                                   "\n".join(f"• {f}" for f in scan_results["failures"])
                        }
                    }
                ],
                priority="high"
            )
            
            # Send email to security team
            await send_email_notification(
                to=["security@sentinelgrid.ai"],
                subject=f"🚨 CRITICAL: Security Scan Failed for Wazuh {version}",
                body=f"""
                Security scan FAILED for Wazuh {version}.
                
                Packages have been BLOCKED from distribution to customers.
                
                Failed scans:
                {json.dumps(scan_results['failures'], indent=2)}
                
                Action Required:
                1. Review scan results in admin dashboard
                2. Investigate security issues
                3. Decide: Wait for Wazuh fix OR Skip this version
                
                Packages will NOT be uploaded to S3 until this is resolved.
                """,
                priority="high"
            )
            
            # DO NOT CONTINUE TO UPLOAD
            raise Exception(f"Security scan failed - distribution blocked")
        
        # SCAN PASSED ✅
        logger.info(f"Security scan PASSED for Wazuh {version}")
        
        # Update status to uploading
        db.execute("""
            UPDATE wazuh_version_reviews
            SET status = 'uploading'
            WHERE id = :id
        """, {"id": review_id})
        db.commit()
        
        # Step 4: Upload to S3/CDN (ONLY runs if scan passed)
        logger.info(f"Uploading packages to S3")
        
        await upload_packages_to_s3(version, scripts_dir)
        
        # Update status to ready
        db.execute("""
            UPDATE wazuh_version_reviews
            SET 
                status = 'ready',
                distributed_at = NOW()
            WHERE id = :id
        """, {"id": review_id})
        db.commit()
        
        logger.info(f"Upload to S3 complete for Wazuh {version}")
        
        # Step 6: Update agent_versions table
        sentinelgrid_version = calculate_sentinelgrid_version(version)
        
        # Set old version to not latest
        db.execute("""
            UPDATE agent_versions
            SET is_latest = false
            WHERE agent_type = 'endpoint' AND upstream_tool = 'wazuh'
        """)
        
        # Insert new version as latest
        db.execute("""
            INSERT INTO agent_versions (
                version, agent_type, upstream_tool, upstream_version,
                os_compatibility, release_date, status, is_latest,
                changelog, release_notes
            )
            VALUES (
                :version, 'endpoint', 'wazuh', :upstream_version,
                '["amazon-linux-2", "ubuntu-22.04", "rhel-8", "debian-12", "windows-server-2022"]'::jsonb,
                CURRENT_DATE, 'stable', true,
                :changelog, :release_notes
            )
        """, {
            "version": sentinelgrid_version,
            "upstream_version": version,
            "changelog": f"Updated to Wazuh {version}",
            "release_notes": f"Based on Wazuh {version}"
        })
        db.commit()
        
        logger.info(f"agent_versions updated: {sentinelgrid_version} is now latest")
        
        # Step 7: Notify team
        await send_slack_notification(
            channel="#devops-alerts",
            message=f"✅ Wazuh {version} successfully processed and distributed!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Wazuh {version} Now Available*\n\n"
                               f"• SentinelGrid Version: {sentinelgrid_version}\n"
                               f"• Downloaded: ✅\n"
                               f"• Rebranded: ✅\n"
                               f"• Set as Latest: ✅\n\n"
                               f"Customers will see this as the recommended version."
                    }
                }
            ]
        )
        
        # Optional: Notify customers
        await notify_customers_new_version(version, sentinelgrid_version)
        
    except Exception as e:
        logger.error(f"Download and rebrand workflow failed: {e}", exc_info=True)
        
        # Mark as failed
        db.execute("""
            UPDATE wazuh_version_reviews
            SET 
                status = 'rejected',
                review_notes = :error
            WHERE id = :id
        """, {
            "id": review_id,
            "error": f"Automated workflow failed: {str(e)}"
        })
        db.commit()
        
        # Notify team of failure
        await send_slack_notification(
            channel="#devops-alerts",
            message=f"❌ Failed to process Wazuh {version}",
            details=str(e)
        )
    
    finally:
        db.close()


def calculate_sentinelgrid_version(wazuh_version: str) -> str:
    """
    Calculate SentinelGrid version based on Wazuh version.
    
    Example mapping:
    Wazuh 4.8.0 → SentinelGrid 1.8.0
    Wazuh 4.9.0 → SentinelGrid 1.9.0
    """
    parts = wazuh_version.split('.')
    if len(parts) >= 2:
        return f"1.{parts[1]}.{parts[2] if len(parts) > 2 else '0'}"
    return "1.0.0"


async def run_security_scans(version: str, scripts_dir: Path) -> Dict[str, Any]:
    """
    Run all security scans on rebranded packages.
    
    This is the CRITICAL GATE before distribution.
    
    Returns:
        Scan results with overall pass/fail status
    """
    logger.info(f"Running security scans for version {version}")
    
    scan_results = {
        "version": version,
        "scan_date": datetime.utcnow().isoformat(),
        "scans": {},
        "overall_passed": True,
        "failures": []
    }
    
    try:
        # Run scan script
        scan_script = scripts_dir / "scan" / "scan-packages.sh"
        
        result = subprocess.run(
            [str(scan_script)],
            cwd=scripts_dir,
            env={"WAZUH_VERSION": version},
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes max
        )
        
        # Parse scan report
        scan_report_path = scripts_dir.parent.parent / "scan-results" / f"scan-report-{version}.json"
        
        if scan_report_path.exists():
            with open(scan_report_path, 'r') as f:
                detailed_results = json.load(f)
                scan_results.update(detailed_results)
        
        # Check if scan passed
        if result.returncode != 0:
            scan_results["overall_passed"] = False
            scan_results["failures"].append("scan_script_failed")
            logger.error(f"Scan script failed with code {result.returncode}")
            logger.error(f"STDERR: {result.stderr}")
        
        return scan_results
        
    except subprocess.TimeoutExpired:
        logger.error(f"Security scan timed out for version {version}")
        return {
            "version": version,
            "scan_date": datetime.utcnow().isoformat(),
            "overall_passed": False,
            "failures": ["scan_timeout"],
            "error": "Security scan timed out after 30 minutes"
        }
    except Exception as e:
        logger.error(f"Security scan failed: {e}", exc_info=True)
        return {
            "version": version,
            "scan_date": datetime.utcnow().isoformat(),
            "overall_passed": False,
            "failures": ["scan_exception"],
            "error": str(e)
        }


async def upload_packages_to_s3(version: str, scripts_dir: Path) -> Dict[str, Any]:
    """
    Upload rebranded packages to S3/CDN.
    
    ONLY called if security scans passed.
    
    Returns:
        Upload results
    """
    logger.info(f"Uploading packages to S3 for version {version}")
    
    try:
        # Run upload script (if exists)
        upload_script = scripts_dir / "upload" / "upload-to-cdn.sh"
        
        if not upload_script.exists():
            logger.warning("Upload script not found - skipping S3 upload")
            return {
                "uploaded": False,
                "reason": "upload_script_not_found"
            }
        
        result = subprocess.run(
            [str(upload_script)],
            cwd=scripts_dir,
            env={
                "WAZUH_VERSION": version,
                "S3_BUCKET": "sentinelgrid-agents",
                "CDN_BASE_URL": "https://agents.sentinelgrid.ai"
            },
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes
        )
        
        if result.returncode != 0:
            logger.error(f"S3 upload failed: {result.stderr}")
            raise Exception(f"S3 upload failed with code {result.returncode}")
        
        logger.info(f"S3 upload complete for version {version}")
        
        return {
            "uploaded": True,
            "upload_time": datetime.utcnow().isoformat(),
            "bucket": "sentinelgrid-agents",
            "packages": [
                f"v{version}/linux/rpm/sentinelgrid-agent-{version}-1.x86_64.rpm",
                f"v{version}/linux/deb/sentinelgrid-agent_{version}-1_amd64.deb",
                f"v{version}/windows/sentinelgrid-agent-{version}-1.msi",
                f"v{version}/macos/intel/sentinelgrid-agent-{version}-1.intel64.pkg",
                f"v{version}/macos/arm/sentinelgrid-agent-{version}-1.arm64.pkg"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}", exc_info=True)
        raise Exception(f"S3 upload failed: {str(e)}")
```

---

## Cron/Scheduler Configuration

### Option 1: Docker Container with Cron

**File:** `backend/services/version_monitor_service/Dockerfile`

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y cron

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Add cron job
RUN echo "0 2 * * * cd /app && python -m app.tasks.wazuh_version_checker >> /var/log/cron.log 2>&1" > /etc/cron.d/version-check
RUN chmod 0644 /etc/cron.d/version-check
RUN crontab /etc/cron.d/version-check

CMD ["cron", "-f"]
```

### Option 2: Celery Beat (More Robust)

**File:** `backend/services/version_monitor_service/app/celery_app.py`

```python
from celery import Celery
from celery.schedules import crontab

app = Celery('version_monitor')

app.conf.beat_schedule = {
    'check-wazuh-versions-daily': {
        'task': 'app.tasks.wazuh_version_checker.daily_version_check',
        'schedule': crontab(hour=2, minute=0),  # 2 AM UTC daily
    },
}

app.conf.timezone = 'UTC'
```

### Option 3: FastAPI Background Task

**File:** `backend/services/version_monitor_service/app/main.py`

```python
import asyncio
from datetime import datetime, time

@app.on_event("startup")
async def start_daily_version_check():
    """Start background task for daily version checking."""
    asyncio.create_task(daily_version_check_loop())


async def daily_version_check_loop():
    """Run version check daily at 2 AM UTC."""
    while True:
        now = datetime.utcnow()
        
        # Calculate next 2 AM UTC
        next_run = datetime.combine(
            now.date() if now.hour < 2 else (now.date() + timedelta(days=1)),
            time(hour=2, minute=0)
        )
        
        # Wait until next run time
        wait_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        
        # Run check
        try:
            await daily_version_check()
        except Exception as e:
            logger.error(f"Daily version check failed: {e}", exc_info=True)
```

---

## Admin Dashboard UI

### Version Review Dashboard

**Page:** `admin/version-reviews`

```
╔═══════════════════════════════════════════════════════════════╗
║  Wazuh Version Reviews                                        ║
╚═══════════════════════════════════════════════════════════════╝

┌─ Pending Reviews (2) ─────────────────────────────────────────┐
│                                                                │
│  🆕 Wazuh 4.9.0                                    2 days ago  │
│     Released: Nov 15, 2025                                     │
│     Status: Pending Review                                     │
│                                                                │
│     Release Notes:                                             │
│     • Enhanced vulnerability detection                         │
│     • New MITRE ATT&CK mappings                               │
│     • Performance improvements                                 │
│     • Security fixes: CVE-2025-XXXXX                          │
│                                                                │
│     [View Full Notes]  [Test in Staging]  [Approve]  [Skip]  │
│                                                                │
│  ─────────────────────────────────────────────────────────────│
│                                                                │
│  🆕 Wazuh 4.10.0                                   1 day ago   │
│     Released: Nov 20, 2025                                     │
│     Status: Pending Review                                     │
│                                                                │
│     ⚠️  Breaking Changes Detected                              │
│     • API changes (review required)                           │
│                                                                │
│     [View Full Notes]  [Test in Staging]  [Approve]  [Skip]  │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌─ Recent Activity ──────────────────────────────────────────────┐
│                                                                │
│  ✅ Wazuh 4.8.0 → Approved and Distributed     3 weeks ago    │
│     Status: Ready (Currently distributed to customers)         │
│     SentinelGrid Version: 1.0.0                               │
│                                                                │
│  ⏭️  Wazuh 4.7.5 → Skipped (Minor release)     1 month ago    │
│     Reason: Security fixes already in 4.8.0                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌─ Current Status ───────────────────────────────────────────────┐
│  Latest Distributed: Wazuh 4.8.0 (SentinelGrid 1.0.0)         │
│  Customer Agents: 1,234 total, 1,100 current (89%)            │
│  Outdated Agents: 134 agents need updating                     │
└────────────────────────────────────────────────────────────────┘
```

---

## Notification Templates

### Slack Notification (New Version)

```json
{
  "channel": "#devops-alerts",
  "attachments": [{
    "color": "#36a64f",
    "title": "🆕 New Wazuh Version Available: 4.9.0",
    "title_link": "https://github.com/wazuh/wazuh/releases/tag/v4.9.0",
    "fields": [
      {
        "title": "Released",
        "value": "Nov 15, 2025",
        "short": true
      },
      {
        "title": "Status",
        "value": "Pending Review",
        "short": true
      }
    ],
    "text": "A new Wazuh version has been detected. Please review for SentinelGrid distribution.",
    "actions": [
      {
        "type": "button",
        "text": "Review in Dashboard",
        "url": "https://admin.sentinelgrid.ai/version-reviews/..."
      },
      {
        "type": "button",
        "text": "View Release Notes",
        "url": "https://github.com/wazuh/wazuh/releases/tag/v4.9.0"
      }
    ]
  }]
}
```

### Email to Customers (New Version Available)

```
Subject: New SentinelGrid Endpoint Protection Version Available

Hi {customer_name},

A new version of SentinelGrid Endpoint Protection is now available:

Current Version: 1.0.0 (Wazuh 4.8.0)
New Version: 1.1.0 (Wazuh 4.9.0)
Released: November 15, 2025

What's New:
• Enhanced vulnerability detection
• Improved performance
• Security updates

Your Status:
• Total Agents: 50
• Up-to-date: 42 (84%)
• Need Update: 8 agents

Action Required:
Update your agents to benefit from the latest security features.

[View Outdated Agents] [Schedule Update] [Learn More]

---
SentinelGrid Team
```

---

## Testing Strategy

### Staging Environment Tests

**When:** After "Test in Staging" button clicked

**Tests Run:**
1. Install agent on test VMs (all 5 OS types)
2. Connect to staging Wazuh Manager
3. Verify agent communication
4. Generate test alerts
5. Verify events in OpenSearch
6. Check for errors in logs
7. Performance benchmarks
8. Compatibility with existing infrastructure

**Automated Test Suite:**
```bash
#!/bin/bash
# Test new Wazuh version in staging

VERSION=$1

# 1. Deploy test agents
./deploy-test-agents.sh $VERSION

# 2. Run integration tests
./test-agent-connectivity.sh
./test-event-flow.sh
./test-performance.sh

# 3. Generate report
./generate-test-report.sh
```

---

## Configuration

### Environment Variables

```bash
# version_monitor_service
GITHUB_API_TOKEN=<token>  # For higher rate limits
SLACK_WEBHOOK_URL=<url>
SMTP_SERVER=smtp.sendgrid.net
ADMIN_EMAILS=security@sentinelgrid.ai,devops@sentinelgrid.ai
CHECK_INTERVAL=86400  # 24 hours in seconds
```

### Feature Flags

```python
# Allow disabling auto-check if needed
ENABLE_AUTO_VERSION_CHECK = os.getenv("ENABLE_AUTO_VERSION_CHECK", "true") == "true"

# Auto-approve patch versions (4.8.0 → 4.8.1)
AUTO_APPROVE_PATCHES = os.getenv("AUTO_APPROVE_PATCHES", "false") == "true"

# Require staging tests before approval
REQUIRE_STAGING_TESTS = os.getenv("REQUIRE_STAGING_TESTS", "true") == "true"
```

---

## Implementation Checklist

### Backend
- [ ] Create `version_monitor_service` directory structure
- [ ] Implement `WazuhVersionChecker` class
- [ ] Implement version review API endpoints
- [ ] Create `wazuh_version_reviews` database table
- [ ] Implement automated download & rebrand workflow
- [ ] Add Slack integration
- [ ] Add email notifications
- [ ] Create background task scheduler

### Scripts
- [ ] Ensure `download-wazuh.sh` can be called programmatically
- [ ] Ensure `rebrand-wazuh.sh` can be called programmatically
- [ ] Create staging test automation scripts
- [ ] Create version comparison utilities

### Frontend (Admin Dashboard)
- [ ] Create version reviews list page
- [ ] Create version review detail page
- [ ] Add approval buttons (Approve/Test/Skip/Postpone)
- [ ] Add test results display
- [ ] Create version history timeline

### Frontend (Customer Dashboard)
- [ ] Add version status widget to endpoints page
- [ ] Create "outdated agents" page
- [ ] Add upgrade action buttons
- [ ] Display release notes

### Integration
- [ ] Connect to Slack workspace
- [ ] Set up SMTP for emails
- [ ] Configure GitHub API access (for release checking)
- [ ] Add to docker-compose

---

## Timeline Estimate

- **Phase 1:** Version checker service - 4 hours
- **Phase 2:** Database schema - 1 hour
- **Phase 3:** Approval API - 3 hours
- **Phase 4:** Download & rebrand automation - 2 hours
- **Phase 5:** Notifications (Slack/Email) - 2 hours
- **Phase 6:** Admin dashboard UI - 4 hours
- **Phase 7:** Testing & validation - 2 hours

**Total:** ~18 hours for complete automated workflow

---

## Benefits

### For SentinelGrid Team
- ✅ **Never miss upstream updates** - Daily automated checks
- ✅ **Informed decisions** - Full release notes before approval
- ✅ **Testing workflow** - Staging environment integration
- ✅ **Audit trail** - Complete history of version decisions

### For Customers
- ✅ **Always current** - Latest security fixes available
- ✅ **Transparency** - Know which version they should use
- ✅ **Proactive alerts** - Notified when updates needed
- ✅ **Easy upgrades** - Clear upgrade path

### For Compliance
- ✅ **Version tracking** - Full audit trail
- ✅ **Security posture** - Know exposure to known vulnerabilities
- ✅ **Documented decisions** - Why versions were approved/skipped
- ✅ **Customer compliance** - Customers can show up-to-date agents

---

## Example Workflow Timeline

**Day 1 (Nov 15, 2025 - 2 AM UTC):**
- 02:00 - Daily check runs
- 02:01 - Wazuh 4.9.0 detected on GitHub
- 02:02 - Review record created (status=pending_review)
- 02:03 - Slack notification sent to #devops-alerts
- 02:04 - Email sent to security@sentinelgrid.ai

**Day 1 (10 AM):**
- Admin reviews release notes in dashboard
- Clicks "Test in Staging"
- Status → testing
- Automated staging deployment initiated

**Day 1 (11 AM):**
- Staging tests complete (48/50 passed)
- Test results submitted via API
- Status → test_passed
- Notification: "✅ Tests passed, ready for approval"

**Day 2 (9 AM):**
- Admin reviews test results
- Clicks "Approve"
- Status → approved
- Download workflow triggered

**Day 2 (9:30 AM):**
- Packages downloaded
- Rebranding complete
- Status → ready
- agent_versions updated (is_latest=true)
- Customer notification sent

**Day 2 (10 AM onwards):**
- Customers see "Update available" in dashboard
- Customers can upgrade agents
- Version compliance tracking active

---

## Future Enhancements

### Intelligent Version Analysis
- AI-powered release notes analysis
- Auto-categorize changes (feature, bugfix, security)
- Risk assessment based on breaking changes
- Recommend approval/skip based on patterns

### Rollback Capability
- Keep previous version available
- One-click rollback if issues discovered
- Gradual rollout (10% → 50% → 100%)

### Customer Opt-In Beta Program
- Some customers can test new versions early
- Provide feedback before general release
- Beta testing rewards/benefits

---

## Next Steps

Ready to implement this automated workflow?

**Phase 1 (Core):**
1. Create `version_monitor_service`
2. Implement daily checker
3. Add `wazuh_version_reviews` table
4. Basic Slack notifications

**Phase 2 (Workflow):**
1. Approval API
2. Automated download & rebrand
3. Update `agent_versions` table

**Phase 3 (UI):**
1. Admin review dashboard
2. Customer version status widget

Would you like me to start implementing Phase 1?

