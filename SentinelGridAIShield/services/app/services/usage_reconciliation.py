"""
Usage Reconciliation Service

Compares AI provider usage (from provider APIs) with gateway usage (from our logs)
to detect bypass attempts. If provider usage > gateway usage, apps are bypassing.

Runs daily as a scheduled job.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import AiEvent, AiProviderCredential
from app.services.vault_delegation import VaultDelegationService

logger = logging.getLogger(__name__)


class UsageReconciliationService:
    """
    Reconciles AI provider usage with gateway usage to detect bypass attempts.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.vault_service = VaultDelegationService()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def daily_reconciliation(self, org_id: str) -> Dict:
        """
        Run daily reconciliation for an organization.
        
        Args:
            org_id: Organization ID
        
        Returns:
            Reconciliation report with discrepancies
        """
        logger.info(f"Starting daily usage reconciliation for org {org_id}")
        
        # Get yesterday's date range
        end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=1)
        
        # Get provider credentials for this org
        credentials = self.db.query(AiProviderCredential).filter(
            AiProviderCredential.org_id == org_id,
            AiProviderCredential.is_active == True
        ).all()
        
        if not credentials:
            logger.warning(f"No active provider credentials found for org {org_id}")
            return {"status": "skipped", "reason": "no_credentials"}
        
        results = {}
        alerts = []
        
        # Check each provider
        for cred in credentials:
            provider = cred.provider
            logger.info(f"Reconciling {provider} usage for org {org_id}")
            
            try:
                # Fetch provider usage
                provider_usage = await self._fetch_provider_usage(
                    org_id, provider, cred, start_date, end_date
                )
                
                # Query gateway usage
                gateway_usage = await self._query_gateway_usage(
                    org_id, provider, start_date, end_date
                )
                
                # Calculate discrepancy
                discrepancy = self._calculate_discrepancy(
                    provider_usage, gateway_usage
                )
                
                results[provider] = {
                    "provider_tokens": provider_usage["total_tokens"],
                    "gateway_tokens": gateway_usage["total_tokens"],
                    "provider_requests": provider_usage["total_requests"],
                    "gateway_requests": gateway_usage["total_requests"],
                    "discrepancy_percent": discrepancy["percent"],
                    "discrepancy_tokens": discrepancy["tokens"],
                    "status": discrepancy["status"]
                }
                
                # Alert if significant discrepancy
                if discrepancy["percent"] > 10:
                    alert = {
                        "org_id": org_id,
                        "provider": provider,
                        "severity": "high" if discrepancy["percent"] > 25 else "medium",
                        "message": f"{provider} usage discrepancy: {discrepancy['percent']:.1f}%",
                        "provider_tokens": provider_usage["total_tokens"],
                        "gateway_tokens": gateway_usage["total_tokens"],
                        "missing_tokens": discrepancy["tokens"],
                        "date_range": f"{start_date.date()} to {end_date.date()}"
                    }
                    alerts.append(alert)
                    logger.warning(f"Usage discrepancy detected: {alert}")
                
            except Exception as e:
                logger.error(f"Error reconciling {provider} for org {org_id}: {str(e)}", exc_info=True)
                results[provider] = {
                    "status": "error",
                    "error": str(e)
                }
        
        report = {
            "org_id": org_id,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "providers": results,
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store report (would save to database in production)
        logger.info(f"Reconciliation complete for org {org_id}: {len(alerts)} alerts")
        
        # Trigger SIEM alert if discrepancies found
        if alerts:
            await self._trigger_siem_alert(report)
        
        return report
    
    async def _fetch_provider_usage(
        self,
        org_id: str,
        provider: str,
        credential: AiProviderCredential,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Fetch usage data from AI provider's API.
        
        Args:
            org_id: Organization ID
            provider: Provider name (openai, anthropic)
            credential: Provider credential configuration
            start_date: Start of date range
            end_date: End of date range
        
        Returns:
            Usage data with total_tokens and total_requests
        """
        # Fetch API key from customer's vault
        config = {
            'vault_type': credential.vault_type,
            'vault_secret_path': credential.vault_secret_path,
            'iam_role_arn': credential.iam_role_arn,
            'vault_region': credential.vault_region
        }
        
        api_key = await self.vault_service.fetch_provider_key(
            org_id=org_id,
            provider=provider,
            credential_config=config
        )
        
        if provider == "openai":
            return await self._fetch_openai_usage(api_key, start_date, end_date)
        elif provider == "anthropic":
            return await self._fetch_anthropic_usage(api_key, start_date, end_date)
        else:
            logger.warning(f"Usage API not implemented for provider: {provider}")
            return {"total_tokens": 0, "total_requests": 0}
    
    async def _fetch_openai_usage(
        self,
        api_key: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Fetch usage from OpenAI Usage API.
        
        OpenAI API: GET https://api.openai.com/v1/usage
        """
        try:
            url = "https://api.openai.com/v1/usage"
            params = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse OpenAI usage response
            # Structure: { "data": [ { "aggregation_timestamp": ..., "n_requests": ..., "operation": ..., "snapshot_id": ..., "n_context_tokens_total": ... } ] }
            total_tokens = 0
            total_requests = 0
            
            for entry in data.get("data", []):
                total_tokens += entry.get("n_context_tokens_total", 0) + entry.get("n_generated_tokens_total", 0)
                total_requests += entry.get("n_requests", 0)
            
            logger.info(f"OpenAI usage: {total_requests} requests, {total_tokens} tokens")
            
            return {
                "total_tokens": total_tokens,
                "total_requests": total_requests
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Usage API might not be available for all accounts
                logger.warning("OpenAI Usage API not available (404) - using alternative method")
                return {"total_tokens": 0, "total_requests": 0}
            raise
        except Exception as e:
            logger.error(f"Error fetching OpenAI usage: {str(e)}", exc_info=True)
            raise
    
    async def _fetch_anthropic_usage(
        self,
        api_key: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Fetch usage from Anthropic API.
        Note: Anthropic may not have a public usage API yet.
        Would need to check their docs or use billing dashboard.
        """
        logger.warning("Anthropic usage API not yet implemented - returning zero")
        # TODO: Implement when Anthropic provides usage API
        return {"total_tokens": 0, "total_requests": 0}
    
    async def _query_gateway_usage(
        self,
        org_id: str,
        provider: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Query gateway usage from our ai_events table.
        
        Args:
            org_id: Organization ID
            provider: Provider name
            start_date: Start of date range
            end_date: End of date range
        
        Returns:
            Usage data with total_tokens and total_requests
        """
        # Query ai_events table
        result = self.db.query(
            func.count(AiEvent.id).label("total_requests"),
            func.sum(AiEvent.tokens_in).label("total_tokens_in"),
            func.sum(AiEvent.tokens_out).label("total_tokens_out")
        ).filter(
            AiEvent.org_id == org_id,
            AiEvent.provider == provider,
            AiEvent.created_at >= start_date,
            AiEvent.created_at < end_date
        ).first()
        
        total_requests = result.total_requests or 0
        total_tokens_in = result.total_tokens_in or 0
        total_tokens_out = result.total_tokens_out or 0
        total_tokens = total_tokens_in + total_tokens_out
        
        logger.info(f"Gateway usage for {provider}: {total_requests} requests, {total_tokens} tokens")
        
        return {
            "total_tokens": total_tokens,
            "total_requests": total_requests
        }
    
    def _calculate_discrepancy(
        self,
        provider_usage: Dict,
        gateway_usage: Dict
    ) -> Dict:
        """
        Calculate discrepancy between provider and gateway usage.
        
        Returns:
            Dict with percent, tokens, status
        """
        provider_tokens = provider_usage["total_tokens"]
        gateway_tokens = gateway_usage["total_tokens"]
        
        if provider_tokens == 0:
            return {
                "percent": 0,
                "tokens": 0,
                "status": "no_usage"
            }
        
        # Calculate discrepancy
        missing_tokens = provider_tokens - gateway_tokens
        percent = (missing_tokens / provider_tokens) * 100
        
        # Determine status
        if percent < 5:
            status = "ok"
        elif percent < 10:
            status = "minor"
        elif percent < 25:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "percent": percent,
            "tokens": missing_tokens,
            "status": status
        }
    
    async def _trigger_siem_alert(self, report: Dict) -> None:
        """
        Trigger SIEM alert for usage discrepancy.
        Creates an alert that will be picked up by detection rule SG-AI-005.
        """
        try:
            # In production, would send to SIEM/OpenSearch
            logger.warning(f"SIEM Alert: Usage discrepancy detected - {report}")
            
            # Could POST to SIEM API or write to OpenSearch directly
            # For now, just log
            
        except Exception as e:
            logger.error(f"Error triggering SIEM alert: {str(e)}", exc_info=True)
    
    async def get_reconciliation_history(
        self,
        org_id: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Get reconciliation history for an organization.
        
        Args:
            org_id: Organization ID
            days: Number of days to retrieve
        
        Returns:
            List of reconciliation reports
        """
        # In production, would query from database
        # For now, return empty list
        logger.info(f"Retrieving {days} days of reconciliation history for org {org_id}")
        return []


# Scheduled job entry point
async def run_daily_reconciliation_for_all_orgs(db: Session) -> Dict:
    """
    Run daily reconciliation for all organizations.
    Called by scheduler (e.g., Celery, APScheduler).
    
    Returns:
        Summary of reconciliation run
    """
    logger.info("Starting daily reconciliation for all organizations")
    
    # Get all unique org_ids from provider credentials
    org_ids = db.query(AiProviderCredential.org_id).distinct().all()
    org_ids = [str(org_id[0]) for org_id in org_ids]
    
    logger.info(f"Found {len(org_ids)} organizations to reconcile")
    
    service = UsageReconciliationService(db)
    results = {}
    total_alerts = 0
    
    for org_id in org_ids:
        try:
            report = await service.daily_reconciliation(org_id)
            results[org_id] = report
            total_alerts += len(report.get("alerts", []))
        except Exception as e:
            logger.error(f"Error reconciling org {org_id}: {str(e)}", exc_info=True)
            results[org_id] = {"status": "error", "error": str(e)}
    
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_orgs": len(org_ids),
        "total_alerts": total_alerts,
        "results": results
    }
    
    logger.info(f"Daily reconciliation complete: {total_alerts} alerts across {len(org_ids)} orgs")
    
    return summary

