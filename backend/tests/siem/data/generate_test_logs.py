"""
Generate realistic test logs for all 10 detection alert types.

This script generates sample log data that can be indexed into OpenSearch
to test the detection monitors and end-to-end incident creation flow.
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import uuid4


class TestLogGenerator:
    """Generates realistic test logs for SIEM detection testing."""
    
    def __init__(self, tenant_id: str, realm: str = "sentinelgrid"):
        """
        Initialize test log generator.
        
        Args:
            tenant_id: Tenant UUID
            realm: Keycloak realm
        """
        self.tenant_id = tenant_id
        self.realm = realm
        self.base_timestamp = datetime.utcnow()
    
    def generate_auth_logs_suspicious_login(self, count: int = 20) -> List[Dict[str, Any]]:
        """
        Generate auth logs for suspicious login detection.
        Pattern: Multiple failures followed by success from same user+IP.
        """
        logs = []
        user_id = f"user-{random.randint(1000, 9999)}"
        user_email = f"test.user{random.randint(100, 999)}@example.com"
        source_ip = f"203.0.113.{random.randint(1, 254)}"
        
        # Generate 7-10 failures
        failure_count = random.randint(7, 10)
        for i in range(failure_count):
            timestamp = self.base_timestamp - timedelta(minutes=10) + timedelta(seconds=i * 30)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "authentication",
                    "type": "start",
                    "outcome": "failure"
                },
                "user": {
                    "id": user_id,
                    "email": user_email,
                    "name": "Test User"
                },
                "source": {
                    "ip": source_ip,
                    "geo": {
                        "country": random.choice(["US", "RU", "CN", "BR"]),
                        "city": "Unknown"
                    }
                },
                "auth": {
                    "reason": "invalid_credentials"
                }
            })
        
        # Generate 1 success
        timestamp = self.base_timestamp - timedelta(minutes=1)
        logs.append({
            "@timestamp": timestamp.isoformat() + "Z",
            "sg": {
                "tenant_id": self.tenant_id,
                "realm": self.realm
            },
            "event": {
                "category": "authentication",
                "type": "start",
                "outcome": "success"
            },
            "user": {
                "id": user_id,
                "email": user_email,
                "name": "Test User"
            },
            "source": {
                "ip": source_ip,
                "geo": {
                    "country": "RU",
                    "city": "Moscow"
                }
            },
            "auth": {
                "method": "password"
            }
        })
        
        return logs
    
    def generate_email_logs_phishing_report(self, count: int = 3) -> List[Dict[str, Any]]:
        """Generate email logs for user-reported phishing."""
        logs = []
        
        for i in range(count):
            timestamp = self.base_timestamp - timedelta(minutes=i * 5)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "email",
                    "type": "phish_report"
                },
                "user": {
                    "id": f"user-{random.randint(100, 999)}",
                    "email": f"user{i}@example.com"
                },
                "email": {
                    "message_id": f"<{uuid4()}@example.com>",
                    "subject": "Urgent: Verify Your Account",
                    "from": "security@fake-bank.example"
                }
            })
        
        return logs
    
    def generate_email_logs_campaign(self, count: int = 50) -> List[Dict[str, Any]]:
        """Generate email logs for phishing campaign detection."""
        logs = []
        subject = "DocuSign: Please review document"
        sender_domain = "docusign-fake.example"
        
        for i in range(count):
            timestamp = self.base_timestamp - timedelta(minutes=30) + timedelta(seconds=i * 10)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "email",
                    "type": "alert"
                },
                "alert": {
                    "subtype": "phishing",
                    "severity": "high"
                },
                "email": {
                    "message_id": f"<campaign-{uuid4()}@{sender_domain}>",
                    "subject": subject,
                    "from": f"noreply@{sender_domain}"
                }
            })
        
        return logs
    
    def generate_endpoint_logs_malware(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate endpoint logs for malware detection."""
        logs = []
        
        malware_names = ["Trojan.Generic.1234", "Backdoor.Agent.XYZ", "Worm.AutoRun.ABC"]
        hosts = ["prod-api-01", "dev-db-02", "worker-03"]
        
        for i in range(count):
            timestamp = self.base_timestamp - timedelta(minutes=i * 3)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "malware",
                    "type": "detection",
                    "severity": random.choice(["high", "critical"])
                },
                "host": {
                    "name": random.choice(hosts),
                    "id": f"host-{random.randint(100, 999)}",
                    "ip": f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}",
                    "asset_criticality": random.choice(["high", "medium", "critical"])
                },
                "user": {
                    "id": f"user-{random.randint(100, 999)}",
                    "name": "svc-api"
                },
                "malware": {
                    "name": random.choice(malware_names),
                    "hash": f"d41d8cd98f00b204e9800998ecf{random.randint(10000, 99999)}"
                }
            })
        
        return logs
    
    def generate_endpoint_logs_ransomware(self, count: int = 2) -> List[Dict[str, Any]]:
        """Generate endpoint logs for ransomware detection."""
        logs = []
        
        ransomware_families = ["LockBit", "Conti", "BlackCat", "REvil"]
        
        for i in range(count):
            timestamp = self.base_timestamp - timedelta(minutes=i * 2)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "malware",
                    "type": "detection",
                    "severity": "critical"
                },
                "malware": {
                    "family": "ransomware",
                    "name": f"{random.choice(ransomware_families)}.VariantX"
                },
                "host": {
                    "name": f"prod-db-{random.randint(10, 99):02d}",
                    "id": f"host-{random.randint(100, 999)}",
                    "asset_criticality": "critical"
                }
            })
        
        return logs
    
    def generate_cloud_posture_logs(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate cloud posture logs for public storage misconfig."""
        logs = []
        
        bucket_names = ["acme-prod-backups", "customer-data", "public-website", "logs-archive"]
        
        for i in range(count):
            timestamp = self.base_timestamp - timedelta(hours=i)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "posture",
                    "type": "finding"
                },
                "posture": {
                    "type": "storage_public",
                    "status": "fail"
                },
                "cloud": {
                    "provider": "aws",
                    "account_id": "111122223333",
                    "region": random.choice(["us-east-1", "us-west-2", "eu-west-1"])
                },
                "resource": {
                    "type": "s3_bucket",
                    "id": random.choice(bucket_names),
                    "tags": {
                        "env": random.choice(["prod", "staging"]),
                        "data_classification": "customer"
                    }
                }
            })
        
        return logs
    
    def generate_iam_audit_logs(self, count: int = 5) -> List[Dict[str, Any]]:
        """Generate IAM audit logs for privilege escalation."""
        logs = []
        
        admin_roles = ["sg_admin", "aws_prod_admin", "idp_global_admin", "admin"]
        
        for i in range(count):
            timestamp = self.base_timestamp - timedelta(hours=i)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "iam",
                    "type": "role_change"
                },
                "iam": {
                    "action": "add_role",
                    "role_name": random.choice(admin_roles)
                },
                "actor": {
                    "id": f"admin-{random.randint(1, 10)}",
                    "email": f"admin{random.randint(1, 5)}@example.com"
                },
                "target_user": {
                    "id": f"user-{random.randint(100, 999)}",
                    "email": f"bob{i}@example.com"
                }
            })
        
        return logs
    
    def generate_auth_logs_password_spray(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate auth logs for password spray detection."""
        logs = []
        attacker_ip = f"198.51.100.{random.randint(1, 254)}"
        
        # Generate failures against 30+ different users
        for i in range(count):
            timestamp = self.base_timestamp - timedelta(minutes=10) + timedelta(seconds=i * 5)
            user_num = random.randint(1, 50)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "authentication",
                    "type": "start",
                    "outcome": "failure"
                },
                "user": {
                    "id": f"user-{user_num}",
                    "email": f"user{user_num}@example.com"
                },
                "source": {
                    "ip": attacker_ip,
                    "geo": {
                        "country": "RU",
                        "city": "Saint Petersburg"
                    }
                },
                "auth": {
                    "reason": "invalid_credentials"
                }
            })
        
        return logs
    
    def generate_network_logs_data_exfil(self, count: int = 20) -> List[Dict[str, Any]]:
        """Generate network logs for data exfiltration detection."""
        logs = []
        user_id = f"user-{random.randint(100, 999)}"
        user_email = f"eve{random.randint(1, 10)}@example.com"
        
        # Generate high volume transfers
        total_bytes = 15 * 1024 * 1024 * 1024  # 15 GB
        bytes_per_log = total_bytes // count
        
        for i in range(count):
            timestamp = self.base_timestamp - timedelta(hours=1) + timedelta(minutes=i * 3)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "network",
                    "type": "connection"
                },
                "user": {
                    "id": user_id,
                    "email": user_email,
                    "department": "engineering"
                },
                "network": {
                    "bytes_out": bytes_per_log,
                    "protocol": "https",
                    "destination": {
                        "ip": f"192.0.2.{random.randint(1, 254)}"
                    }
                }
            })
        
        return logs
    
    def generate_device_logs_lost(self, count: int = 2) -> List[Dict[str, Any]]:
        """Generate device logs for lost/stolen device detection."""
        logs = []
        
        platforms = ["macOS", "Windows", "iOS", "Android"]
        
        for i in range(count):
            timestamp = self.base_timestamp - timedelta(minutes=i * 10)
            logs.append({
                "@timestamp": timestamp.isoformat() + "Z",
                "sg": {
                    "tenant_id": self.tenant_id,
                    "realm": self.realm
                },
                "event": {
                    "category": "device",
                    "type": "status_change"
                },
                "device": {
                    "id": f"device-{uuid4().hex[:12]}",
                    "platform": random.choice(platforms),
                    "owner_user_id": f"user-{random.randint(100, 999)}",
                    "owner_email": f"sam{i}@example.com",
                    "status": random.choice(["lost", "stolen"])
                },
                "report": {
                    "source": "mdm",
                    "reported_by": "mdm-system"
                }
            })
        
        return logs
    
    def generate_all_test_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate all test data for all 10 detection types."""
        return {
            "auth_suspicious_login": self.generate_auth_logs_suspicious_login(20),
            "email_phishing_report": self.generate_email_logs_phishing_report(5),
            "email_campaign": self.generate_email_logs_campaign(50),
            "endpoint_malware": self.generate_endpoint_logs_malware(5),
            "endpoint_ransomware": self.generate_endpoint_logs_ransomware(2),
            "cloud_posture_public_storage": self.generate_cloud_posture_logs(10),
            "iam_privilege_escalation": self.generate_iam_audit_logs(5),
            "auth_password_spray": self.generate_auth_logs_password_spray(100),
            "network_data_exfil": self.generate_network_logs_data_exfil(20),
            "device_lost": self.generate_device_logs_lost(2)
        }
    
    def export_to_files(self, output_dir: str = "./test_data"):
        """Export all test data to NDJSON files."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        all_data = self.generate_all_test_data()
        
        for data_type, logs in all_data.items():
            filename = f"{output_dir}/{data_type}.ndjson"
            with open(filename, "w") as f:
                for log in logs:
                    f.write(json.dumps(log) + "\n")
            
            print(f"Generated {len(logs)} logs for {data_type} -> {filename}")
        
        print(f"\nTotal logs generated: {sum(len(logs) for logs in all_data.values())}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test logs for SIEM detection")
    parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant UUID"
    )
    parser.add_argument(
        "--realm",
        default="sentinelgrid",
        help="Keycloak realm"
    )
    parser.add_argument(
        "--output-dir",
        default="./test_data",
        help="Output directory for NDJSON files"
    )
    
    args = parser.parse_args()
    
    generator = TestLogGenerator(tenant_id=args.tenant_id, realm=args.realm)
    generator.export_to_files(output_dir=args.output_dir)
    
    print("\n✓ Test data generation completed!")
    print(f"\nNext steps:")
    print(f"1. Index data into OpenSearch:")
    print(f"   curl -X POST 'http://localhost:9200/_bulk' \\")
    print(f"        -H 'Content-Type: application/x-ndjson' \\")
    print(f"        --data-binary @test_data/auth_suspicious_login.ndjson")
    print(f"\n2. Wait for monitors to fire (check monitor schedules)")
    print(f"\n3. Verify incidents created in SOAR")


if __name__ == "__main__":
    main()

