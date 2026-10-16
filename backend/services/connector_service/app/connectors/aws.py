"""AWS Cloud connector (CloudTrail, GuardDuty)."""

import logging
import boto3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from app.connectors.base import BaseConnector
from app.models.event import RawEvent

logger = logging.getLogger(__name__)


class AWSConnector(BaseConnector):
    """Connector for AWS CloudTrail and GuardDuty."""
    
    def __init__(self, config: Dict[str, Any], tenant_id: str):
        super().__init__(config, tenant_id)
        self.cloudtrail_client = None
        self.guardduty_client = None
        self.sts_client = None
        self.account_id = config.get("account_id")
        self.regions = config.get("regions", ["us-east-1"])
        self.services = config.get("services", ["cloudtrail"])
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AWS clients using IAM role assumption."""
        try:
            # Extract credentials/role configuration
            credentials_config = self.config.get("credentials", {})
            role_arn = credentials_config.get("role_arn")
            external_id = credentials_config.get("external_id")
            
            if role_arn:
                # Use role assumption
                sts = boto3.client("sts", region_name=self.regions[0])
                
                assume_role_params = {
                    "RoleArn": role_arn,
                    "RoleSessionName": f"SentinelGrid-{self.tenant_id}",
                }
                if external_id:
                    assume_role_params["ExternalId"] = external_id
                
                assumed_role = sts.assume_role(**assume_role_params)
                credentials = assumed_role["Credentials"]
                
                session = boto3.Session(
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                )
            else:
                # Use direct credentials (less secure, for dev/testing)
                access_key = credentials_config.get("access_key_id")
                secret_key = credentials_config.get("secret_access_key")
                
                if not access_key or not secret_key:
                    raise ValueError("Missing AWS credentials or role_arn in config")
                
                session = boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                )
            
            # Initialize clients for each region
            self.clients = {}
            for region in self.regions:
                self.clients[region] = {
                    "cloudtrail": session.client("cloudtrail", region_name=region),
                    "guardduty": session.client("guardduty", region_name=region),
                }
            
            # Default to first region
            self.cloudtrail_client = self.clients[self.regions[0]]["cloudtrail"]
            self.guardduty_client = self.clients[self.regions[0]]["guardduty"]
            
        except ClientError as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to AWS."""
        try:
            # Test CloudTrail access
            if "cloudtrail" in self.services:
                self.cloudtrail_client.describe_trails(maxResults=1)
            
            # Test GuardDuty access
            if "guardduty" in self.services:
                try:
                    detector_ids = self.guardduty_client.list_detectors()["DetectorIds"]
                    if detector_ids:
                        self.guardduty_client.get_detector(DetectorId=detector_ids[0])
                except ClientError as e:
                    if e.response["Error"]["Code"] != "BadRequestException":
                        raise
            
            return True
        except Exception as e:
            logger.error(f"AWS connection test failed: {e}")
            return False
    
    def fetch_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[RawEvent]:
        """
        Fetch events from AWS CloudTrail and GuardDuty.
        
        Args:
            start_time: Start time for event range
            end_time: End time for event range
            limit: Maximum number of events to fetch
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if not end_time:
            end_time = datetime.utcnow()
        
        events = []
        
        # Fetch CloudTrail events
        if "cloudtrail" in self.services:
            cloudtrail_events = self._fetch_cloudtrail_events(start_time, end_time, limit)
            events.extend(cloudtrail_events)
        
        # Fetch GuardDuty findings
        if "guardduty" in self.services:
            guardduty_events = self._fetch_guardduty_findings(start_time, end_time, limit)
            events.extend(guardduty_events)
        
        return events[:limit] if limit else events
    
    def _fetch_cloudtrail_events(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: Optional[int]
    ) -> List[RawEvent]:
        """Fetch CloudTrail events."""
        events = []
        
        try:
            # Look up events
            paginator = self.cloudtrail_client.get_paginator("lookup_events")
            pages = paginator.paginate(
                LookupAttributes=[
                    # Add filters if needed
                ],
                StartTime=start_time,
                EndTime=end_time,
                MaxResults=min(limit or 50, 50),  # AWS limit is 50 per request
            )
            
            for page in pages:
                for event in page.get("Events", []):
                    # Parse CloudTrail event
                    cloudtrail_event = event.get("CloudTrailEvent")
                    if cloudtrail_event:
                        import json
                        event_data = json.loads(cloudtrail_event)
                        
                        # Determine event type
                        event_type = "aws.cloudtrail"
                        event_name = event_data.get("eventName", "")
                        if "CreateUser" in event_name or "CreateRole" in event_name:
                            event_type = "aws.iam.create"
                        elif "DeleteUser" in event_name or "DeleteRole" in event_name:
                            event_type = "aws.iam.delete"
                        elif "Attach" in event_name or "PutRolePolicy" in event_name:
                            event_type = "aws.iam.modify"
                        elif "ConsoleLogin" in event_name:
                            event_type = "aws.login.success"
                        elif "AuthorizeSecurityGroupIngress" in event_name:
                            event_type = "aws.ec2.security_group.modify"
                        elif "PutBucketPolicy" in event_name or "PutBucketAcl" in event_name:
                            event_type = "aws.s3.policy.modify"
                        
                        raw_event = {
                            "event_type": event_type,
                            "event_name": event_name,
                            "user": {
                                "name": event_data.get("userIdentity", {}).get("userName"),
                                "arn": event_data.get("userIdentity", {}).get("arn"),
                                "type": event_data.get("userIdentity", {}).get("type"),
                            },
                            "source_ip": event_data.get("sourceIPAddress"),
                            "user_agent": event_data.get("userAgent"),
                            "aws_region": event_data.get("awsRegion"),
                            "resource_type": event_data.get("resources", [{}])[0].get("resourceType") if event_data.get("resources") else None,
                            "resource_name": event_data.get("resources", [{}])[0].get("resourceName") if event_data.get("resources") else None,
                            "request_parameters": event_data.get("requestParameters", {}),
                            "response_elements": event_data.get("responseElements", {}),
                            "timestamp": event.get("EventTime"),
                        }
                        
                        events.append(self.normalize_event(raw_event))
                
                if limit and len(events) >= limit:
                    break
        
        except ClientError as e:
            logger.error(f"Failed to fetch CloudTrail events: {e}")
            # Don't raise, return what we have
        
        return events
    
    def _fetch_guardduty_findings(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: Optional[int]
    ) -> List[RawEvent]:
        """Fetch GuardDuty findings."""
        events = []
        
        try:
            # Get detector IDs for all regions
            for region in self.regions:
                guardduty = self.clients[region]["guardduty"]
                
                try:
                    detector_ids = guardduty.list_detectors()["DetectorIds"]
                    if not detector_ids:
                        continue
                    
                    detector_id = detector_ids[0]  # Use first detector
                    
                    # List findings
                    paginator = guardduty.get_paginator("list_findings")
                    finding_criteria = {
                        "Criterion": {
                            "updatedAt": {
                                "Gte": int(start_time.timestamp() * 1000),
                                "Lt": int(end_time.timestamp() * 1000),
                            }
                        }
                    }
                    
                    pages = paginator.paginate(
                        DetectorId=detector_id,
                        FindingCriteria=finding_criteria,
                        MaxResults=min(limit or 50, 50),
                    )
                    
                    for page in pages:
                        finding_ids = page.get("FindingIds", [])
                        
                        if finding_ids:
                            # Get finding details
                            findings_response = guardduty.get_findings(
                                DetectorId=detector_id,
                                FindingIds=finding_ids[:50]  # AWS limit
                            )
                            
                            for finding in findings_response.get("Findings", []):
                                raw_event = {
                                    "event_type": "aws.guardduty.finding",
                                    "finding_type": finding.get("Type"),
                                    "severity": finding.get("Severity"),
                                    "title": finding.get("Title"),
                                    "description": finding.get("Description"),
                                    "resource": finding.get("Resource", {}),
                                    "service": finding.get("Service", {}),
                                    "account_id": finding.get("AccountId"),
                                    "region": finding.get("Region"),
                                    "timestamp": finding.get("UpdatedAt"),
                                }
                                
                                events.append(self.normalize_event(raw_event))
                        
                        if limit and len(events) >= limit:
                            break
                    
                    if limit and len(events) >= limit:
                        break
                
                except ClientError as e:
                    if e.response["Error"]["Code"] == "BadRequestException":
                        # No GuardDuty enabled in this region
                        continue
                    logger.warning(f"Failed to fetch GuardDuty findings for region {region}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to fetch GuardDuty findings: {e}")
            # Don't raise, return what we have
        
        return events
    
    def fetch_users(self) -> List[Dict[str, Any]]:
        """Fetch AWS IAM users (not typically used, but for consistency)."""
        users = []
        
        try:
            # Use first region for IAM (IAM is global, but boto3 needs a region)
            iam = boto3.client("iam", region_name="us-east-1")
            
            paginator = iam.get_paginator("list_users")
            for page in paginator.paginate():
                for user in page.get("Users", []):
                    # Get user details
                    user_details = {
                        "id": user["UserName"],
                        "name": user["UserName"],
                        "arn": user["Arn"],
                        "created_at": user.get("CreateDate").isoformat() if user.get("CreateDate") else None,
                        "status": "active",  # AWS doesn't have a direct status field
                    }
                    
                    # Get last login (from password last used)
                    if user.get("PasswordLastUsed"):
                        user_details["last_login"] = user["PasswordLastUsed"].isoformat()
                    
                    users.append(user_details)
        
        except ClientError as e:
            logger.error(f"Failed to fetch AWS IAM users: {e}")
            # Don't raise, return what we have
        
        return users
    
    def normalize_event(self, raw_event: Dict[str, Any]) -> RawEvent:
        """Normalize AWS event to ECS format."""
        timestamp = raw_event.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif not timestamp:
            timestamp = datetime.utcnow()
        elif isinstance(timestamp, datetime):
            pass
        else:
            # Handle AWS timestamp (could be int or other format)
            timestamp = datetime.utcnow()
        
        return RawEvent(
            event_type=raw_event.get("event_type", "aws.unknown"),
            source="aws_cloudtrail" if "cloudtrail" in raw_event.get("event_type", "") else "aws_guardduty",
            timestamp=timestamp,
            raw_data=raw_event,
            tenant_id=self.tenant_id,
            metadata={
                "connector_type": "aws",
                "account_id": self.account_id,
                "fetched_at": datetime.utcnow().isoformat(),
            }
        )
    
    def get_source_name(self) -> str:
        return "aws_cloudtrail"
    
    def get_connector_type(self) -> str:
        return "aws"

