"""
OpenSearch Index State Management (ISM) policies for SentinelGrid.

Manages index lifecycle: hot → warm → cold → delete.
Applies retention policies to control storage costs.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Default retention settings (configurable via env vars)
HOT_DAYS = int(os.getenv("OPENSEARCH_HOT_DAYS", "7"))
WARM_DAYS = int(os.getenv("OPENSEARCH_WARM_DAYS", "30"))
DELETE_DAYS = int(os.getenv("OPENSEARCH_DELETE_DAYS", "90"))
ROLLOVER_SIZE_GB = int(os.getenv("OPENSEARCH_ROLLOVER_SIZE_GB", "10"))
ROLLOVER_AGE_DAYS = int(os.getenv("OPENSEARCH_ROLLOVER_AGE_DAYS", "1"))


def get_ism_policy() -> dict:
    """Get the ISM policy for SentinelGrid log indices.

    Lifecycle:
    1. Hot phase (0-7 days): Normal indexing, 30s refresh, 1 replica
    2. Warm phase (7-30 days): Read-only, force merge to 1 segment, 60s refresh
    3. Cold phase (30-90 days): Read-only, 0 replicas, minimal resources
    4. Delete phase (90+ days): Index deleted
    """
    return {
        "policy": {
            "description": "SentinelGrid log index lifecycle management",
            "default_state": "hot",
            "states": [
                {
                    "name": "hot",
                    "actions": [
                        {
                            "rollover": {
                                "min_size": f"{ROLLOVER_SIZE_GB}gb",
                                "min_index_age": f"{ROLLOVER_AGE_DAYS}d"
                            }
                        }
                    ],
                    "transitions": [
                        {
                            "state_name": "warm",
                            "conditions": {
                                "min_index_age": f"{HOT_DAYS}d"
                            }
                        }
                    ]
                },
                {
                    "name": "warm",
                    "actions": [
                        {"read_only": {}},
                        {"force_merge": {"max_num_segments": 1}},
                        {
                            "index_priority": {"priority": 50}
                        }
                    ],
                    "transitions": [
                        {
                            "state_name": "cold",
                            "conditions": {
                                "min_index_age": f"{WARM_DAYS}d"
                            }
                        }
                    ]
                },
                {
                    "name": "cold",
                    "actions": [
                        {"read_only": {}},
                        {
                            "replica_count": {"number_of_replicas": 0}
                        }
                    ],
                    "transitions": [
                        {
                            "state_name": "delete",
                            "conditions": {
                                "min_index_age": f"{DELETE_DAYS}d"
                            }
                        }
                    ]
                },
                {
                    "name": "delete",
                    "actions": [
                        {"delete": {}}
                    ],
                    "transitions": []
                }
            ],
            "ism_template": [
                {
                    "index_patterns": ["sg-*"],
                    "priority": 100
                }
            ]
        }
    }


async def ensure_ism_policy(opensearch_client) -> bool:
    """Create or update the ISM policy in OpenSearch.

    Args:
        opensearch_client: OpenSearch client instance

    Returns:
        True if policy was created/updated, False on error
    """
    policy_id = "sg-log-lifecycle"
    policy = get_ism_policy()

    try:
        # Check if policy exists
        try:
            existing = opensearch_client.transport.perform_request(
                "GET", f"/_plugins/_ism/policies/{policy_id}"
            )
            # Update existing policy
            seq_no = existing.get("_seq_no", 0)
            primary_term = existing.get("_primary_term", 1)
            opensearch_client.transport.perform_request(
                "PUT",
                f"/_plugins/_ism/policies/{policy_id}?if_seq_no={seq_no}&if_primary_term={primary_term}",
                body=policy
            )
            logger.info(f"Updated ISM policy '{policy_id}'")
        except Exception:
            # Create new policy
            opensearch_client.transport.perform_request(
                "PUT",
                f"/_plugins/_ism/policies/{policy_id}",
                body=policy
            )
            logger.info(f"Created ISM policy '{policy_id}'")

        return True
    except Exception as e:
        logger.error(f"Failed to create/update ISM policy: {e}")
        return False


def get_index_template_settings() -> dict:
    """Get optimized index template settings.

    Returns settings dict to use when creating index templates.
    """
    return {
        "index": {
            "refresh_interval": "30s",
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "codec": "best_compression",
            "plugins": {
                "index_state_management": {
                    "rollover_alias": ""  # Set per-index
                }
            }
        }
    }
