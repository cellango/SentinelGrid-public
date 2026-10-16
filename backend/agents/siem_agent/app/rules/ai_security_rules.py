"""
AI Security Detection Rules for SentinelGridAIShield
Maps to OWASP LLM Top 10 and MITRE ATT&CK/ATLAS
"""

AI_SECURITY_RULES = [
    {
        "id": "SG-AI-001",
        "name": "PII/Secret Outbound to External LLM",
        "description": "Detects when prompts or responses containing PII or secrets are sent to external SaaS LLM providers and are not fully blocked by policy",
        "severity": "high",  # Critical if has_secrets
        "category": "AI Security",
        "data_source": "sg-ai-events-*",
        "query": {
            "bool": {
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": "now-10m",
                                "lte": "now"
                            }
                        }
                    },
                    {
                        "terms": {
                            "provider": ["openai", "anthropic", "azure", "cohere", "other_external"]
                        }
                    },
                    {
                        "bool": {
                            "should": [
                                {"term": {"has_pii": True}},
                                {"term": {"has_secrets": True}}
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    {
                        "bool": {
                            "must_not": [
                                {"term": {"policy_decision": "blocked"}}
                            ]
                        }
                    }
                ]
            }
        },
        "threshold": {
            "type": "any",  # Any single event triggers
            "count": 1
        },
        "owasp_mapping": "LLM02 - Sensitive Information Disclosure",
        "mitre_mapping": ["T1567 - Exfiltration to Cloud Storage"],
        "mitre_atlas": ["Data Exfiltration from AI Systems"],
        "trigger_playbook": "AI-001-Data-Leak",
        "alert_fields": ["org_id", "ai_app_id", "user_id", "provider", "model", "has_pii", "has_secrets"],
        "response_actions": [
            "Create critical incident",
            "Block external LLM providers for app",
            "Notify security team",
            "Trigger SOAR playbook AI-001"
        ]
    },
    {
        "id": "SG-AI-002",
        "name": "Prompt Injection Burst",
        "description": "Detects a burst of prompts flagged as prompt injection / jailbreak attempts concentrated on a single user/app",
        "severity": "medium",  # Escalate to high for privileged apps
        "category": "AI Security",
        "data_source": "sg-ai-events-*",
        "query": {
            "bool": {
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": "now-10m",
                                "lte": "now"
                            }
                        }
                    },
                    {
                        "term": {
                            "prompt_injection_suspected": True
                        }
                    }
                ]
            }
        },
        "aggregation": {
            "by_user_app": {
                "composite": {
                    "size": 1000,
                    "sources": [
                        {"org": {"terms": {"field": "org_id"}}},
                        {"app": {"terms": {"field": "ai_app_id"}}},
                        {"user": {"terms": {"field": "user_id"}}}
                    ]
                },
                "aggs": {
                    "event_count": {
                        "value_count": {"field": "id"}
                    }
                }
            }
        },
        "threshold": {
            "type": "aggregated",
            "count": 3,
            "time_window": "10m",
            "condition": "event_count >= 3"
        },
        "owasp_mapping": "LLM01 - Prompt Injection",
        "mitre_mapping": ["TA0001 - Initial Access"],
        "mitre_atlas": ["Adversarial Prompting", "Manipulate Model via Input"],
        "trigger_playbook": "AI-002-Prompt-Injection",
        "alert_fields": ["org_id", "ai_app_id", "user_id", "event_count"],
        "response_actions": [
            "Create medium incident",
            "Pull last 50 AI events for context",
            "AI SOC classification (benign vs malicious)",
            "Apply rate throttle if not allowlisted",
            "Notify app owner",
            "Trigger SOAR playbook AI-002"
        ]
    },
    {
        "id": "SG-AI-003",
        "name": "Excessive AI Policy Violations",
        "description": "Detects AI applications that repeatedly hit guardrails, indicating misconfiguration or attempted misuse",
        "severity": "medium",
        "category": "AI Security",
        "data_source": "sg-ai-events-*",
        "query": {
            "bool": {
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": "now-15m",
                                "lte": "now"
                            }
                        }
                    },
                    {
                        "term": {
                            "policy_decision": "blocked"
                        }
                    }
                ]
            }
        },
        "aggregation": {
            "by_app": {
                "terms": {
                    "field": "ai_app_id",
                    "size": 100
                },
                "aggs": {
                    "violation_count": {
                        "value_count": {"field": "id"}
                    }
                }
            }
        },
        "threshold": {
            "type": "aggregated",
            "count": 5,
            "time_window": "15m",
            "condition": "violation_count >= 5"
        },
        "owasp_mapping": "LLM06/LLM08 - Permission Issues / Excessive Agency",
        "mitre_mapping": ["TA0003 - Persistence", "TA0005 - Defense Evasion"],
        "mitre_atlas": ["Excessive Agency", "Unsafe Tool Use"],
        "trigger_playbook": "AI-003-Policy-Violation",
        "alert_fields": ["org_id", "ai_app_id", "violation_count", "violation_reasons"],
        "response_actions": [
            "Create medium incident",
            "Notify app owner",
            "Optionally disable app temporarily",
            "Review app configuration",
            "Trigger SOAR playbook AI-003"
        ]
    },
    {
        "id": "SG-AI-004",
        "name": "Direct AI Provider Access Detected",
        "description": "Detects when an endpoint/host makes a direct connection to AI provider APIs bypassing the SentinelGrid gateway",
        "severity": "critical",
        "category": "AI Security - Bypass Attempt",
        "data_source": "wazuh-alerts-*",
        "query": {
            "bool": {
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": "now-5m",
                                "lte": "now"
                            }
                        }
                    },
                    {
                        "terms": {
                            "rule.id": ["100401", "100402"]  # Wazuh rule IDs from centralized config
                        }
                    }
                ]
            }
        },
        "threshold": {
            "type": "any",
            "count": 1
        },
        "owasp_mapping": "LLM Security Bypass",
        "mitre_mapping": ["T1071.001 - Application Layer Protocol"],
        "mitre_atlas": ["Bypass Security Controls"],
        "trigger_playbook": "AI-004-Gateway-Bypass",
        "alert_fields": ["agent.name", "agent.id", "data.dstip", "data.dstport", "data.process"],
        "response_actions": [
            "Create critical incident",
            "Identify source host and process",
            "Check why network policies didn't block",
            "Revoke app's gateway API key",
            "Notify security team immediately",
            "Trigger SOAR playbook AI-004"
        ]
    },
    {
        "id": "SG-AI-005",
        "name": "Endpoint Protection Tampering Detected",
        "description": "Detects tampering with Wazuh agent (SentinelGrid Endpoint Protection) configuration or service",
        "severity": "high",
        "category": "AI Security - Defense Evasion",
        "data_source": "wazuh-alerts-*",
        "query": {
            "bool": {
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": "now-5m",
                                "lte": "now"
                            }
                        }
                    },
                    {
                        "terms": {
                            "rule.id": ["100403", "100404", "80004", "80005"]
                        }
                    }
                ]
            }
        },
        "threshold": {
            "type": "any",
            "count": 1
        },
        "owasp_mapping": "Defense Evasion",
        "mitre_mapping": ["T1562.001 - Impair Defenses: Disable or Modify Tools"],
        "mitre_atlas": ["Disable Security Tools"],
        "trigger_playbook": "AI-005-Agent-Tampering",
        "alert_fields": ["agent.name", "agent.id", "rule.description", "data.file", "data.process"],
        "response_actions": [
            "Create high incident",
            "Identify user who modified agent",
            "Check for correlated AI bypass attempts",
            "Restore agent configuration from manager",
            "Investigate potential host compromise",
            "Trigger SOAR playbook AI-005"
        ]
    },
    {
        "id": "SG-AI-006",
        "name": "AI Telemetry Gap Detected",
        "description": "Detects when a host with AI applications stops sending telemetry, indicating possible agent tampering or bypass",
        "severity": "medium",
        "category": "AI Security - Anomaly",
        "data_source": "sg-ai-events-*",
        "query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": "now-60m",
                                "lte": "now-30m"
                            }
                        }
                    }
                ],
                "must_not": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": "now-30m",
                                "lte": "now"
                            }
                        }
                    }
                ]
            }
        },
        "aggregation": {
            "by_host": {
                "terms": {
                    "field": "host.name",
                    "size": 1000
                },
                "aggs": {
                    "last_30min_events": {
                        "filter": {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-30m"
                                }
                            }
                        }
                    },
                    "prev_30min_events": {
                        "filter": {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-60m",
                                    "lte": "now-30m"
                                }
                            }
                        }
                    }
                }
            }
        },
        "threshold": {
            "type": "correlation",
            "condition": "prev_30min_events > 0 AND last_30min_events == 0"
        },
        "owasp_mapping": "Monitoring Gap",
        "mitre_mapping": ["T1562 - Impair Defenses"],
        "mitre_atlas": ["Evade Monitoring"],
        "trigger_playbook": "AI-006-Telemetry-Gap",
        "alert_fields": ["host.name", "org_id", "last_seen", "expected_apps"],
        "response_actions": [
            "Create medium incident",
            "Check Wazuh agent status",
            "Verify AI apps still running",
            "Query provider usage API for discrepancy",
            "If gap confirmed, escalate to AI-004",
            "Trigger SOAR playbook AI-006"
        ]
    }
]

def get_ai_security_rules():
    """Returns all AI security detection rules"""
    return AI_SECURITY_RULES

def get_rule_by_id(rule_id: str):
    """Get a specific AI security rule by ID"""
    for rule in AI_SECURITY_RULES:
        if rule["id"] == rule_id:
            return rule
    return None

