"""OpenSearch monitor definitions (legacy 10) with catalog expansion."""

import logging
from pathlib import Path
from typing import Dict, Any, List

import yaml

logger = logging.getLogger(__name__)

_SOC2_DEFAULTS: Dict[str, List[str]] = {
    "identity": ["CC6.1", "CC4.1"],
    "phish": ["CC2.1", "CC6.1", "CC4.1"],
    "endpoint": ["CC6.1", "CC7.1", "CC4.1"],
    "network": ["CC7.1", "CC4.1"],
    "cloud": ["CC7.1", "CC8.1", "CC9.1"],
    "vuln": ["CC7.1", "CC8.1", "CC9.1"],
    "exec": ["CC1.1", "CC2.1"],
    "ai": ["CC2.1", "CC3.1"],
}


def _derive_soc2(entry: Dict[str, Any]) -> List[str]:
    incident = (
        entry.get("incident_type")
        or entry.get("category")
        or entry.get("owner")
        or entry.get("alert_type")
        or ""
    ).lower()
    severity = (entry.get("severity") or "").lower()
    criteria: set[str] = set()
    for key, mapped in _SOC2_DEFAULTS.items():
        if key in incident:
            criteria.update(mapped)
    if "public_exposure" in incident:
        criteria.update(["CC7.1", "CC8.1", "CC9.1"])
    if severity in ("high", "critical"):
        criteria.add("CC3.1")
    if not criteria:
        criteria.add("CC4.1")
    return sorted(criteria)


def _build_query_from_catalog(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight query builder from catalog entry + parameters."""
    params = entry.get("parameters") or {}
    lookback = params.get("lookback", "10m")
    filters: List[Dict[str, Any]] = [
        {"range": {"@timestamp": {"gte": f"now-{lookback}"}}},
        {"term": {"sg.tenant_id": "{tenant_id}"}},
    ]
    # Optional refinements based on common parameter keys
    if "roles" in params:
        filters.append({"terms": {"target_role.keyword": params["roles"]}})
    if "groups" in params:
        filters.append({"terms": {"group.name.keyword": params["groups"]}})
    if "ports" in params:
        filters.append({"terms": {"destination.port": params["ports"]}})
    if "subtype" in params:
        filters.append({"term": {"subtype": params["subtype"]}})
    return {
        "size": 0,
        "query": {
            "bool": {
                "filter": filters
            }
        }
    }


def _build_trigger_from_catalog(entry: Dict[str, Any]) -> Dict[str, Any]:
    threshold = entry.get("parameters", {}).get("threshold", 1)
    return {
        "script": {
            "source": f"return ctx.results[0].hits.total.value >= {threshold};"
        }
    }


def _load_catalog_monitors() -> List[Dict[str, Any]]:
    """
    Load monitor definitions from cfg/detections/catalog.yaml.
    Falls back to empty list if file missing or errors (legacy monitors still used).
    """
    try:
        # __file__ = /app/app/config/monitor_definitions.py (in container)
        # parents[2] -> /app
        path = Path(__file__).resolve().parents[2] / "cfg" / "detections" / "catalog.yaml"
        if not path.exists():
            return []
        data = yaml.safe_load(path.read_text()) or {}
        detections = data.get("detections") or []
        monitors: List[Dict[str, Any]] = []
        for det in detections:
            monitors.append({
                "rule_key": det.get("id"),
                "name": det.get("name"),
                "description": det.get("incident_type") or det.get("default_playbook_key") or "",
                "category": det.get("category", "identity"),
                "version": "1.0.0",
                "severity": det.get("severity", "medium"),
                "alert_type": det.get("alert_type") or det.get("incident_type") or det.get("category"),
                "playbook_id": det.get("default_playbook_key"),
                "index_pattern": "sg-{tenant_id}-*",
                "schedule": {"period": {"interval": 5, "unit": "MINUTES"}},
                "query": _build_query_from_catalog(det),
                "trigger_condition": _build_trigger_from_catalog(det),
                "metadata": {
                    "mitre_techniques": det.get("mitre_techniques") or [],
                    "mitre_tactics": det.get("mitre_tactics") or [],
                    "nist_controls": det.get("nist_controls") or [],
                    "soc2_criteria": det.get("soc2_criteria") or _derive_soc2(det),
                }
            })
        return monitors
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to load catalog monitors: %s", exc)
        return []

# All 10 detection monitor definitions
# These will be deployed to OpenSearch Alerting plugin per tenant

DETECTION_MONITORS: List[Dict[str, Any]] = [
    {
        "rule_key": "SG-DET-001",
        "name": "Suspicious Login / Account Takeover",
        "description": "Detects suspicious login patterns: multiple failures followed by success from same user+IP",
        "category": "identity",
        "version": "1.0.0",
        "severity": "high",
        "alert_type": "suspicious_login",
        "playbook_id": "PLAYBOOK_ACCOUNT_TAKEOVER",
        "index_pattern": "sg-{tenant_id}-auth-*",
        "schedule": {
            "period": {"interval": 5, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-10m", "lte": "now"}}},
                        {"term": {"event.category": "authentication"}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}}
                    ]
                }
            },
            "aggs": {
                "by_user_ip": {
                    "composite": {
                        "size": 1000,
                        "sources": [
                            {"user": {"terms": {"field": "user.id"}}},
                            {"ip": {"terms": {"field": "source.ip"}}}
                        ]
                    },
                    "aggs": {
                        "failures": {
                            "filter": {"term": {"event.outcome": "failure"}}
                        },
                        "successes": {
                            "filter": {"term": {"event.outcome": "success"}}
                        },
                        "first_failure": {
                            "min": {"field": "@timestamp"}
                        },
                        "last_success": {
                            "max": {
                                "field": "@timestamp",
                                "script": {
                                    "source": "doc['event.outcome'].value == 'success' ? doc['@timestamp'].value.toEpochMilli() : null"
                                }
                            }
                        }
                    }
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": """
                    def buckets = ctx.results[0].aggregations.by_user_ip.buckets;
                    for (bucket in buckets) {
                        if (bucket.failures.doc_count >= 5 && bucket.successes.doc_count >= 1) {
                            return true;
                        }
                    }
                    return false;
                """
            }
        },
        "metadata": {
            "mitre_techniques": ["T1078", "T1110"],
            "mitre_tactics": ["TA0001", "TA0006"],
            "nist_controls": ["AC-2", "AC-7", "IA-2", "IR-4"],
            "cis_controls": ["4", "5", "6"]
        }
    },
    {
        "rule_key": "SG-DET-002",
        "name": "User-Reported Phishing",
        "description": "User reports suspicious email via phishing@company or report button",
        "category": "email",
        "version": "1.0.0",
        "severity": "medium",
        "alert_type": "phishing_user_report",
        "playbook_id": "PLAYBOOK_PHISHING_USER_REPORTED",
        "index_pattern": "sg-{tenant_id}-email-*",
        "schedule": {
            "period": {"interval": 5, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-5m", "lte": "now"}}},
                        {"term": {"event.category": "email"}},
                        {"term": {"event.type": "phish_report"}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}}
                    ]
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": "return ctx.results[0].hits.total.value > 0;"
            }
        },
        "metadata": {
            "mitre_techniques": ["T1566.001", "T1566.002"],
            "mitre_tactics": ["TA0001"],
            "nist_controls": ["IR-4", "IR-5", "AC-2"],
            "cis_controls": ["4", "7", "8"]
        }
    },
    {
        "rule_key": "SG-DET-003",
        "name": "Email Security Phishing Campaign",
        "description": "Email gateway detects high-severity phishing campaign",
        "category": "email",
        "version": "1.0.0",
        "severity": "high",
        "alert_type": "phishing_campaign",
        "playbook_id": "PLAYBOOK_EMAIL_CAMPAIGN",
        "index_pattern": "sg-{tenant_id}-email-*",
        "schedule": {
            "period": {"interval": 10, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-10m", "lte": "now"}}},
                        {"term": {"event.category": "email"}},
                        {"term": {"event.type": "alert"}},
                        {"term": {"alert.subtype": "phishing"}},
                        {"terms": {"alert.severity": ["high", "critical"]}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}}
                    ]
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": "return ctx.results[0].hits.total.value >= 1;"
            }
        },
        "metadata": {
            "mitre_techniques": ["T1566.001", "T1566.002"],
            "mitre_tactics": ["TA0001"],
            "nist_controls": ["IR-4", "IR-5"],
            "cis_controls": ["7", "8"]
        }
    },
    {
        "rule_key": "SG-DET-004",
        "name": "Endpoint Malware Detection",
        "description": "High-severity malware detected on endpoint",
        "category": "endpoint",
        "version": "1.0.0",
        "severity": "high",
        "alert_type": "endpoint_malware",
        "playbook_id": "PLAYBOOK_ENDPOINT_MALWARE",
        "index_pattern": "sg-{tenant_id}-endpoint-*",
        "schedule": {
            "period": {"interval": 5, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-5m", "lte": "now"}}},
                        {"term": {"event.category": "malware"}},
                        {"terms": {"event.severity": ["high", "critical"]}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}}
                    ]
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": "return ctx.results[0].hits.total.value > 0;"
            }
        },
        "metadata": {
            "mitre_techniques": ["T1059", "T1055", "T1204"],
            "mitre_tactics": ["TA0002", "TA0005"],
            "nist_controls": ["SI-3", "SI-4", "IR-4"],
            "cis_controls": ["8", "10"]
        }
    },
    {
        "rule_key": "SG-DET-005",
        "name": "Ransomware Suspected",
        "description": "Ransomware family detected or suspected based on behavior",
        "category": "endpoint",
        "version": "1.0.0",
        "severity": "critical",
        "alert_type": "ransomware_suspected",
        "playbook_id": "PLAYBOOK_RANSOMWARE",
        "index_pattern": "sg-{tenant_id}-endpoint-*",
        "schedule": {
            "period": {"interval": 5, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-5m", "lte": "now"}}},
                        {"term": {"event.category": "malware"}},
                        {"term": {"malware.family": "ransomware"}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}}
                    ]
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": "return ctx.results[0].hits.total.value > 0;"
            }
        },
        "metadata": {
            "mitre_techniques": ["T1486", "T1490", "T1059"],
            "mitre_tactics": ["TA0040", "TA0002"],
            "nist_controls": ["SI-3", "CP-9", "CP-10", "IR-4"],
            "cis_controls": ["10", "11"]
        }
    },
    {
        "rule_key": "SG-DET-006",
        "name": "Public Cloud Storage Misconfiguration",
        "description": "Cloud storage bucket configured with public access",
        "category": "cloud",
        "version": "1.0.0",
        "severity": "high",
        "alert_type": "cloud_storage_public",
        "playbook_id": "PLAYBOOK_PUBLIC_STORAGE",
        "index_pattern": "sg-{tenant_id}-cloud-posture-*",
        "schedule": {
            "period": {"interval": 15, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-15m", "lte": "now"}}},
                        {"term": {"event.category": "posture"}},
                        {"term": {"posture.type": "storage_public"}},
                        {"term": {"posture.status": "fail"}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}}
                    ],
                    "must_not": [
                        {"term": {"resource.tags.sg_public_ok": True}}
                    ]
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": "return ctx.results[0].hits.total.value > 0;"
            }
        },
        "metadata": {
            "mitre_techniques": ["T1530"],
            "mitre_tactics": ["TA0009"],
            "nist_controls": ["AC-3", "AC-6", "IR-4"],
            "cis_controls": ["14"]
        }
    },
    {
        "rule_key": "SG-DET-007",
        "name": "Privilege Escalation / New Admin",
        "description": "User granted admin role or privileged access",
        "category": "identity",
        "version": "1.0.0",
        "severity": "high",
        "alert_type": "privilege_escalation",
        "playbook_id": "PLAYBOOK_PRIVILEGE_ESCALATION",
        "index_pattern": "sg-{tenant_id}-iam-audit-*",
        "schedule": {
            "period": {"interval": 10, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-10m", "lte": "now"}}},
                        {"term": {"event.category": "iam"}},
                        {"term": {"event.type": "role_change"}},
                        {"term": {"iam.action": "add_role"}},
                        {"terms": {"iam.role.name": ["sg_admin", "aws_prod_admin", "idp_global_admin", "admin"]}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}}
                    ]
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": "return ctx.results[0].hits.total.value > 0;"
            }
        },
        "metadata": {
            "mitre_techniques": ["T1078", "T1098", "T1136"],
            "mitre_tactics": ["TA0004", "TA0003"],
            "nist_controls": ["AC-2", "AC-6", "IA-4", "IR-4"],
            "cis_controls": ["4", "5", "6"]
        }
    },
    {
        "rule_key": "SG-DET-008",
        "name": "Password Spray / Brute Force",
        "description": "Many failed login attempts against multiple users from single IP",
        "category": "identity",
        "version": "1.0.0",
        "severity": "medium",
        "alert_type": "password_spray",
        "playbook_id": "PLAYBOOK_PASSWORD_SPRAY",
        "index_pattern": "sg-{tenant_id}-auth-*",
        "schedule": {
            "period": {"interval": 10, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-10m", "lte": "now"}}},
                        {"term": {"event.category": "authentication"}},
                        {"term": {"event.outcome": "failure"}},
                        {"term": {"auth.reason": "invalid_credentials"}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}}
                    ]
                }
            },
            "aggs": {
                "by_ip": {
                    "terms": {"field": "source.ip", "size": 1000},
                    "aggs": {
                        "user_count": {"cardinality": {"field": "user.id"}}
                    }
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": """
                    def buckets = ctx.results[0].aggregations.by_ip.buckets;
                    for (bucket in buckets) {
                        if (bucket.doc_count >= 50 && bucket.user_count.value >= 10) {
                            return true;
                        }
                    }
                    return false;
                """
            }
        },
        "metadata": {
            "mitre_techniques": ["T1110.003", "T1110.004"],
            "mitre_tactics": ["TA0006"],
            "nist_controls": ["AC-7", "IA-2", "IR-4"],
            "cis_controls": ["4", "6"]
        }
    },
    {
        "rule_key": "SG-DET-009",
        "name": "Data Exfiltration / Unusual Transfer",
        "description": "Unusually large data transfer detected (>10GB in 1h per user)",
        "category": "network",
        "version": "1.0.0",
        "severity": "high",
        "alert_type": "data_exfil_suspected",
        "playbook_id": "PLAYBOOK_DATA_EXFIL",
        "index_pattern": "sg-{tenant_id}-network-*,sg-{tenant_id}-dlp-*",
        "schedule": {
            "period": {"interval": 60, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-1h", "lte": "now"}}},
                        {"term": {"event.category": "network"}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}}
                    ]
                }
            },
            "aggs": {
                "by_user": {
                    "terms": {"field": "user.id", "size": 1000},
                    "aggs": {
                        "bytes_out": {"sum": {"field": "network.bytes_out"}}
                    }
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": """
                    def buckets = ctx.results[0].aggregations.by_user.buckets;
                    for (bucket in buckets) {
                        if (bucket.bytes_out.value >= 10000000000L) {
                            return true;
                        }
                    }
                    return false;
                """
            }
        },
        "metadata": {
            "mitre_techniques": ["T1041", "T1048", "T1020"],
            "mitre_tactics": ["TA0010"],
            "nist_controls": ["AC-4", "AU-2", "SC-7", "IR-4"],
            "cis_controls": ["13"]
        }
    },
    {
        "rule_key": "SG-DET-010",
        "name": "Lost / Stolen Device",
        "description": "Device marked as lost/stolen in MDM or user report",
        "category": "device",
        "version": "1.0.0",
        "severity": "medium",
        "alert_type": "lost_device",
        "playbook_id": "PLAYBOOK_LOST_DEVICE",
        "index_pattern": "sg-{tenant_id}-device-*,sg-{tenant_id}-incidents-*",
        "schedule": {
            "period": {"interval": 15, "unit": "MINUTES"}
        },
        "query": {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": "now-15m", "lte": "now"}}},
                        {"term": {"sg.tenant_id": "{tenant_id}"}},
                        {
                            "bool": {
                                "should": [
                                    {
                                        "bool": {
                                            "filter": [
                                                {"term": {"event.category": "device"}},
                                                {"terms": {"device.status": ["lost", "stolen"]}}
                                            ]
                                        }
                                    },
                                    {
                                        "bool": {
                                            "filter": [
                                                {"term": {"event.type": "lost_report"}}
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        },
        "trigger_condition": {
            "script": {
                "source": "return ctx.results[0].hits.total.value > 0;"
            }
        },
        "metadata": {
            "mitre_techniques": ["T1200", "T1091"],
            "mitre_tactics": ["TA0001"],
            "nist_controls": ["MP-6", "AC-19", "IR-4"],
            "cis_controls": ["13"]
        }
    }
]


def get_monitor_definition(rule_key: str) -> Dict[str, Any]:
    """Get monitor definition by rule key."""
    catalog_monitors = _load_catalog_monitors()
    monitors = catalog_monitors if catalog_monitors else DETECTION_MONITORS
    for monitor in monitors:
        if monitor.get("rule_key") == rule_key:
            return monitor
    raise ValueError(f"Monitor definition not found for rule key: {rule_key}")


def get_all_monitor_definitions() -> List[Dict[str, Any]]:
    """Get all monitor definitions."""
    catalog_monitors = _load_catalog_monitors()
    if catalog_monitors:
        return catalog_monitors
    return DETECTION_MONITORS


def interpolate_tenant_id(monitor_def: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """
    Replace {tenant_id} placeholders in monitor definition with actual tenant ID.
    
    Args:
        monitor_def: Monitor definition dictionary
        tenant_id: Tenant UUID
    
    Returns:
        Monitor definition with interpolated tenant ID
    """
    import json
    import copy
    
    # Deep copy to avoid modifying original
    interpolated = copy.deepcopy(monitor_def)
    
    # Convert to JSON string, replace, and parse back
    json_str = json.dumps(interpolated)
    json_str = json_str.replace("{tenant_id}", tenant_id)
    
    return json.loads(json_str)
