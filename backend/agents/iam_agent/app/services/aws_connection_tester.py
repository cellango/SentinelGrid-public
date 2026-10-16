"""
AWS Connection Tester Service

Tests AWS cross-account role assumption for onboarding.
"""

import logging
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AWSConnectionTester:
    """Service for testing AWS cross-account role connections."""

    def __init__(self):
        """Initialize AWS connection tester."""
        self.sts_client = boto3.client('sts', region_name='us-east-1')

    def test_role_assumption(
        self,
        role_arn: str,
        external_id: str,
        session_name: str = "SentinelGridConnectionTest"
    ) -> Dict[str, Any]:
        """
        Test assuming an AWS IAM role with external ID.

        Args:
            role_arn: ARN of the IAM role to assume
            external_id: External ID for the role assumption
            session_name: Name for the assumed role session

        Returns:
            Dictionary with test results:
            {
                "success": bool,
                "message": str,
                "account_id": str (if successful),
                "user_id": str (if successful),
                "error": str (if failed)
            }
        """
        try:
            # Validate ARN format
            if not role_arn.startswith("arn:aws:iam::"):
                return {
                    "success": False,
                    "message": "Invalid IAM Role ARN format",
                    "error": "ARN must start with 'arn:aws:iam::'"
                }

            # Extract account ID from ARN
            arn_parts = role_arn.split(":")
            if len(arn_parts) < 6:
                return {
                    "success": False,
                    "message": "Invalid IAM Role ARN format",
                    "error": "ARN format is incorrect"
                }

            # Attempt to assume the role
            logger.info(f"Testing role assumption: {role_arn} with external_id: {external_id[:8]}...")

            response = self.sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=session_name,
                ExternalId=external_id,
                DurationSeconds=900  # 15 minutes
            )

            # If successful, get account info
            credentials = response['Credentials']
            assumed_role_identity = response['AssumedRoleUser']

            # Test that we can use the credentials
            test_sts = boto3.client(
                'sts',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken']
            )

            caller_identity = test_sts.get_caller_identity()

            logger.info(f"Successfully assumed role: {role_arn}")
            logger.info(f"Account ID: {caller_identity.get('Account')}")

            return {
                "success": True,
                "message": "Successfully assumed role and verified access",
                "account_id": caller_identity.get('Account'),
                "user_id": caller_identity.get('UserId'),
                "arn": caller_identity.get('Arn'),
                "assumed_role_arn": assumed_role_identity.get('Arn'),
                "credentials": credentials,
            }

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            logger.error(f"AWS ClientError testing role assumption: {error_code} - {error_message}")

            # Provide user-friendly error messages
            if error_code == 'AccessDenied':
                if 'ExternalId' in error_message:
                    return {
                        "success": False,
                        "message": "External ID mismatch. Please verify you used the correct External ID from the SentinelGrid UI.",
                        "error": error_message
                    }
                else:
                    return {
                        "success": False,
                        "message": "Access denied. Please verify the role ARN and that the role trusts SentinelGrid's account.",
                        "error": error_message
                    }
            elif error_code == 'InvalidClientTokenId':
                return {
                    "success": False,
                    "message": "Invalid credentials. Please check your AWS configuration.",
                    "error": error_message
                }
            elif error_code == 'NoSuchEntity':
                return {
                    "success": False,
                    "message": "Role not found. Please verify the role ARN is correct.",
                    "error": error_message
                }
            else:
                return {
                    "success": False,
                    "message": f"AWS error: {error_code}",
                    "error": error_message
                }

        except BotoCoreError as e:
            logger.error(f"BotoCore error testing role assumption: {e}")
            return {
                "success": False,
                "message": "AWS service error. Please try again later.",
                "error": str(e)
            }

        except Exception as e:
            logger.error(f"Unexpected error testing role assumption: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Unexpected error during connection test",
                "error": str(e)
            }

    def test_log_access(
        self,
        role_arn: str,
        external_id: str,
        log_groups: Optional[list] = None,
        s3_buckets: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Optional health: attempt to read from provided CWL log groups and S3 buckets.
        Returns success plus per-target results; does not fail if resources are missing.
        """
        results: Dict[str, Any] = {"success": True, "logs": {}, "s3": {}}
        try:
            assume = self.test_role_assumption(role_arn, external_id)
            if not assume.get("success"):
                return {**assume, "success": False}

            creds = assume.get("credentials") or {}
            # Re-assume with STS to get credentials if not returned
            sts_resp = self.sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName="SGLogHealth",
                ExternalId=external_id,
                DurationSeconds=900
            )
            credentials = sts_resp["Credentials"]

            if log_groups:
                logs_client = boto3.client(
                    "logs",
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                )
                for lg in log_groups:
                    try:
                        streams = logs_client.describe_log_streams(logGroupName=lg, limit=1)
                        results["logs"][lg] = {
                            "status": "ok",
                            "streams": len(streams.get("logStreams", []))
                        }
                    except Exception as e:
                        results["logs"][lg] = {"status": "error", "error": str(e)}
                        results["success"] = False

            if s3_buckets:
                s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                )
                for bucket in s3_buckets:
                    try:
                        # Strip arn to bucket name if needed
                        bucket_name = bucket.replace("arn:aws:s3:::", "").split("/")[0]
                        s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                        results["s3"][bucket] = {"status": "ok"}
                    except Exception as e:
                        results["s3"][bucket] = {"status": "error", "error": str(e)}
                        results["success"] = False

            return results
        except Exception as e:
            logger.error(f"Error testing log access: {e}", exc_info=True)
            return {"success": False, "error": str(e), "logs": results.get("logs", {}), "s3": results.get("s3", {})}

    def validate_account_id(self, account_id: str) -> bool:
        """
        Validate AWS account ID format.

        Args:
            account_id: AWS account ID to validate

        Returns:
            True if valid, False otherwise
        """
        return account_id.isdigit() and len(account_id) == 12

    def validate_role_arn(self, role_arn: str) -> bool:
        """
        Validate IAM role ARN format.

        Args:
            role_arn: IAM role ARN to validate

        Returns:
            True if valid, False otherwise
        """
        if not role_arn.startswith("arn:aws:iam::"):
            return False

        parts = role_arn.split(":")
        if len(parts) < 6:
            return False

        # Check account ID part (should be 12 digits)
        account_id = parts[4]
        if not self.validate_account_id(account_id):
            return False

        # Check role name part
        if not parts[5].startswith("role/"):
            return False

        return True
