"""
Seed detection monitors for a tenant.

This script:
1. Creates webhook destination in OpenSearch Notifications
2. Deploys all 10 detection monitors for the tenant
3. Stores monitor IDs in database for management
"""

import asyncio
import argparse
import sys
import os
import logging
import json
from uuid import UUID
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.monitor_manager import MonitorManager
from app.config.monitor_definitions import get_all_monitor_definitions
from app.core.config import settings
from app.core.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def seed_monitors_for_tenant(
    tenant_id: str,
    soar_webhook_url: str,
    auth_token: str,
    dry_run: bool = False,
    reuse_destination: bool = True,
    use_router_destination: bool = False,
):
    """
    Seed all detection monitors for a tenant.
    
    Args:
        tenant_id: Tenant UUID
        soar_webhook_url: SOAR webhook endpoint URL
        auth_token: Internal service token for authentication
        dry_run: If True, don't actually create monitors
        reuse_destination: If True, reuse existing destination_id from DB when present
    """
    logger.info(f"Seeding monitors for tenant {tenant_id}")
    logger.info(f"SOAR webhook: {soar_webhook_url}")
    
    if dry_run:
        logger.warning("DRY RUN MODE - No monitors will be created")
    
    manager = MonitorManager()
    db = SessionLocal()

    try:
        router_destination_id = None
        if use_router_destination and not dry_run:
            router_destination_id = await manager.create_router_destination()
            logger.info(f"Using shared router destination: {router_destination_id}")

        # Load rule_id map for persistence
        rule_rows = db.execute(
            text("SELECT id, rule_key, current_version FROM detection_rules")
        ).mappings().all()
        rule_map = {row["rule_key"]: row for row in rule_rows}

        # Optionally reuse existing destination for this tenant
        existing_destination_id = None
        if reuse_destination and not dry_run:
            row = db.execute(
                text(
                    "SELECT opensearch_destination_id, custom_config "
                    "FROM tenant_detection_monitors "
                    "WHERE tenant_id = CAST(:tenant_id AS uuid) "
                    "AND opensearch_destination_id IS NOT NULL "
                    "LIMIT 1"
                ),
                {"tenant_id": tenant_id},
            ).mappings().first()
            if row:
                existing_destination_id = row.get("opensearch_destination_id")
                logger.info(f"Reusing existing destination_id: {existing_destination_id}")

        # Step 1: Create webhook destination
        if not dry_run:
            if router_destination_id:
                destination_id = router_destination_id
            elif existing_destination_id:
                destination_id = existing_destination_id
            else:
                logger.info("Creating webhook destination...")
                destination_id = await manager.create_webhook_destination(
                    tenant_id=tenant_id,
                    webhook_url=soar_webhook_url,
                    auth_token=auth_token
                )
                logger.info(f"Created webhook destination: {destination_id}")
        else:
            destination_id = "dry-run-destination-id"
            logger.info(f"[DRY RUN] Would create webhook destination")
        
        # Step 2: Deploy all 10 monitors
        monitor_definitions = get_all_monitor_definitions()
        deployed_monitors = []
        
        for monitor_def in monitor_definitions:
            rule_key = monitor_def["rule_key"]
            logger.info(f"Deploying monitor: {rule_key} - {monitor_def['name']}")
            rule_row = rule_map.get(rule_key)
            if not rule_row:
                logger.warning(f"  ✗ No detection_rules row found for rule_key={rule_key}, skipping DB record")
            
            if not dry_run:
                try:
                    result = await manager.create_monitor(
                        tenant_id=tenant_id,
                        rule_key=rule_key,
                        destination_id=destination_id
                    )
                    deployed_monitors.append(result)
                    logger.info(f"  ✓ Created monitor {result['monitor_id']}")

                    if rule_row:
                        db.execute(
                            text(
                                """
                                INSERT INTO tenant_detection_monitors (
                                    tenant_id, rule_id, rule_version, opensearch_monitor_id, opensearch_destination_id,
                                    is_enabled, custom_config, deployed_at, last_updated, approval_status
                                ) VALUES (
                                    CAST(:tenant_id AS uuid), CAST(:rule_id AS uuid), :rule_version, :monitor_id, :destination_id,
                                    true, :custom_config, NOW(), NOW(), 'approved'
                                )
                                ON CONFLICT (tenant_id, rule_id) DO UPDATE SET
                                    rule_version = EXCLUDED.rule_version,
                                    opensearch_monitor_id = EXCLUDED.opensearch_monitor_id,
                                    opensearch_destination_id = EXCLUDED.opensearch_destination_id,
                                    is_enabled = true,
                                    custom_config = EXCLUDED.custom_config,
                                    approval_status = 'approved',
                                    last_updated = NOW()
                                """
                            ),
                            {
                                "tenant_id": tenant_id,
                                "rule_id": str(rule_row["id"]),
                                "rule_version": rule_row.get("current_version") or monitor_def.get("version") or "1.0.0",
                                "monitor_id": result["monitor_id"],
                                "destination_id": destination_id,
                                "custom_config": json.dumps({
                                    "soar_webhook_url": soar_webhook_url,
                                    "auth_token": auth_token,
                                }),
                            },
                        )
                except Exception as e:
                    logger.error(f"  ✗ Failed to create monitor {rule_key}: {e}")
                    continue
            else:
                logger.info(f"  [DRY RUN] Would create monitor for {rule_key}")
        
        # Step 3: Summary + persist
        if not dry_run:
            db.commit()
        logger.info("\nSummary:")
        logger.info(f"  Tenant: {tenant_id}")
        logger.info(f"  Destination ID: {destination_id}")
        logger.info(f"  Monitors deployed: {len(deployed_monitors)}/{len(monitor_definitions)}")
        
        if deployed_monitors:
            logger.info("\nDeployed monitors:")
            for monitor in deployed_monitors:
                logger.info(f"  - {monitor['rule_key']}: {monitor['monitor_id']}")
        
        return {
            "tenant_id": tenant_id,
            "destination_id": destination_id,
            "monitors": deployed_monitors,
            "total": len(deployed_monitors)
        }
        
    except Exception as e:
        logger.error(f"Error seeding monitors: {e}", exc_info=True)
        raise
    finally:
        db.close()


async def list_tenant_monitors(tenant_id: str):
    """List all monitors for a tenant."""
    logger.info(f"Listing monitors for tenant {tenant_id}")
    
    manager = MonitorManager()
    
    try:
        monitors = await manager.list_monitors(tenant_id=tenant_id)
        
        if not monitors:
            logger.info("No monitors found for this tenant")
            return []
        
        logger.info(f"\nFound {len(monitors)} monitors:")
        for monitor in monitors:
            monitor_id = monitor.get("_id", "unknown")
            name = monitor.get("name", "unknown")
            enabled = monitor.get("enabled", False)
            status = "✓ enabled" if enabled else "✗ disabled"
            
            logger.info(f"  {status} {monitor_id}: {name}")
        
        return monitors
        
    except Exception as e:
        logger.error(f"Error listing monitors: {e}", exc_info=True)
        raise


async def delete_tenant_monitors(tenant_id: str, confirm: bool = False):
    """Delete all monitors for a tenant."""
    logger.warning(f"Deleting monitors for tenant {tenant_id}")
    
    if not confirm:
        logger.error("Must pass --confirm flag to delete monitors")
        return
    
    manager = MonitorManager()
    
    try:
        monitors = await manager.list_monitors(tenant_id=tenant_id)
        
        if not monitors:
            logger.info("No monitors found for this tenant")
            return
        
        logger.info(f"Found {len(monitors)} monitors to delete")
        
        deleted_count = 0
        for monitor in monitors:
            monitor_id = monitor.get("_id")
            name = monitor.get("name", "unknown")
            
            try:
                success = await manager.delete_monitor(monitor_id)
                if success:
                    logger.info(f"  ✓ Deleted {monitor_id}: {name}")
                    deleted_count += 1
                else:
                    logger.warning(f"  ✗ Failed to delete {monitor_id}: {name}")
            except Exception as e:
                logger.error(f"  ✗ Error deleting {monitor_id}: {e}")
        
        logger.info(f"\nDeleted {deleted_count}/{len(monitors)} monitors")
        
    except Exception as e:
        logger.error(f"Error deleting monitors: {e}", exc_info=True)
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage OpenSearch detection monitors for tenants"
    )
    parser.add_argument(
        "action",
        choices=["seed", "list", "delete"],
        help="Action to perform"
    )
    parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant UUID"
    )
    parser.add_argument(
        "--soar-url",
        default=os.getenv("SOAR_AGENT_URL", "http://soar_agent:8000") + "/api/v1/detection-events/ingest",
        help="SOAR webhook URL (default: from settings)"
    )
    parser.add_argument(
        "--auth-token",
        default=settings.INTERNAL_SERVICE_TOKEN,
        help="Internal service token (default: from settings)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually create monitors (for testing)"
    )
    parser.add_argument(
        "--no-reuse-destination",
        action="store_true",
        help="Force creation of a new destination even if one exists"
    )
    parser.add_argument(
        "--use-router-destination",
        action="store_true",
        help="Use shared router destination instead of per-tenant destination"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm deletion (required for delete action)"
    )
    
    args = parser.parse_args()
    
    # Validate tenant ID format
    try:
        UUID(args.tenant_id)
    except ValueError:
        logger.error(f"Invalid tenant ID format: {args.tenant_id}")
        sys.exit(1)
    
    # Run action
    if args.action == "seed":
        result = asyncio.run(
            seed_monitors_for_tenant(
                tenant_id=args.tenant_id,
                soar_webhook_url=args.soar_url,
                auth_token=args.auth_token,
                dry_run=args.dry_run,
                reuse_destination=not args.no_reuse_destination,
                use_router_destination=args.use_router_destination,
            )
        )
        logger.info("\n✓ Monitor seeding completed successfully")
        
    elif args.action == "list":
        asyncio.run(list_tenant_monitors(args.tenant_id))
        
    elif args.action == "delete":
        asyncio.run(delete_tenant_monitors(args.tenant_id, args.confirm))


if __name__ == "__main__":
    main()
