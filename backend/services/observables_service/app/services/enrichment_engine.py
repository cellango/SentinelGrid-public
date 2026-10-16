"""Enrichment engine for observables."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models import Observable, ObservableAnalyzer, ObservableType
from app.services.cortex_service import CortexService
from app.core.config import settings

logger = logging.getLogger(__name__)


class EnrichmentEngine:
    """Engine for enriching observables via Cortex analyzers."""
    
    def __init__(self, db: Session):
        self.db = db
        self.cortex = CortexService()
    
    def _get_analyzers_for_type(self, observable_type: str) -> List[str]:
        """
        Get recommended analyzers for an observable type.
        
        Args:
            observable_type: Type of observable
        
        Returns:
            List of analyzer IDs
        """
        # Mapping of observable types to Cortex analyzer IDs
        analyzer_mapping = {
            ObservableType.IP: [
                "AbuseIPDB_1_0",
                "VirusTotal_GetReport_3_0",
                "PassiveDNS_2_0",
            ],
            ObservableType.DOMAIN: [
                "VirusTotal_GetReport_3_0",
                "PassiveDNS_2_0",
                "Whois_2_0",
            ],
            ObservableType.URL: [
                "VirusTotal_GetReport_3_0",
                "URLhaus_2_0",
            ],
            ObservableType.HASH: [
                "VirusTotal_GetReport_3_0",
                "MalwareBazaar_2_0",
            ],
            ObservableType.EMAIL: [
                "EmailRep_1_0",
            ],
            ObservableType.USER_ID: [
                "SentinelGrid_UserInfo_1_0",
            ],
            ObservableType.CVE: [
                "CVESearch_2_0",
            ],
        }
        
        return analyzer_mapping.get(observable_type, [])
    
    async def enrich_observable(
        self,
        observable_id: UUID,
        analyzer_ids: Optional[List[str]] = None,
        force: bool = False,
    ) -> Observable:
        """
        Enrich an observable using Cortex analyzers.
        
        Args:
            observable_id: Observable ID to enrich
            analyzer_ids: Specific analyzers to run (None = auto-select)
            force: Force re-enrichment even if recently enriched
        
        Returns:
            Updated observable
        """
        observable = self.db.query(Observable).filter(Observable.id == observable_id).first()
        if not observable:
            raise ValueError(f"Observable {observable_id} not found")
        
        # Check if enrichment is needed
        if not force and observable.enrichment_status == "completed":
            # Check TTL
            if observable.enrichment_data:
                enriched_at = observable.enrichment_data.get("enriched_at")
                if enriched_at:
                    enriched_time = datetime.fromisoformat(enriched_at)
                    ttl = timedelta(hours=settings.ENRICHMENT_TTL_HOURS)
                    if datetime.utcnow() - enriched_time < ttl:
                        logger.info(f"Observable {observable_id} enrichment still fresh, skipping")
                        return observable
        
        # Update status
        observable.enrichment_status = "enriching"
        self.db.commit()
        
        try:
            # Create observable in Cortex
            cortex_obs = await self.cortex.create_observable(
                data_type=observable.observable_type,
                data=observable.value,
                tlp=observable.tlp_level,
            )
            cortex_obs_id = cortex_obs.get("id")
            
            # Determine which analyzers to run
            if not analyzer_ids:
                analyzer_ids = self._get_analyzers_for_type(observable.observable_type)
            
            # Run analyzers
            enrichment_results = {}
            for analyzer_id in analyzer_ids:
                try:
                    # Create analyzer job record
                    analyzer_job = ObservableAnalyzer(
                        observable_id=observable_id,
                        analyzer_id=analyzer_id,
                        status="running",
                        started_at=datetime.utcnow(),
                    )
                    self.db.add(analyzer_job)
                    self.db.commit()
                    
                    # Run analyzer in Cortex
                    job = await self.cortex.run_analyzer(
                        analyzer_id=analyzer_id,
                        observable_id=cortex_obs_id,
                    )
                    
                    cortex_job_id = job.get("id")
                    analyzer_job.cortex_job_id = cortex_job_id
                    self.db.commit()
                    
                    # Wait for job to complete (with timeout)
                    report = await self.cortex.wait_for_job(cortex_job_id, timeout=120)
                    
                    # Update analyzer job with results
                    analyzer_job.status = report.get("status", "completed").lower()
                    analyzer_job.report = report.get("report")
                    analyzer_job.completed_at = datetime.utcnow()
                    self.db.commit()
                    
                    # Store enrichment data
                    enrichment_results[analyzer_id] = {
                        "status": analyzer_job.status,
                        "report": report.get("report", {}).get("full", {}),
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to run analyzer {analyzer_id}: {e}")
                    analyzer_job.status = "failed"
                    analyzer_job.error_message = str(e)
                    analyzer_job.completed_at = datetime.utcnow()
                    self.db.commit()
            
            # Update observable with enrichment data
            observable.enrichment_data = {
                "enriched_at": datetime.utcnow().isoformat(),
                "analyzers": enrichment_results,
                "cortex_observable_id": cortex_obs_id,
            }
            observable.enrichment_status = "completed"
            self.db.commit()
            
            logger.info(f"Successfully enriched observable {observable_id}")
            return observable
        
        except Exception as e:
            logger.error(f"Failed to enrich observable {observable_id}: {e}")
            observable.enrichment_status = "failed"
            self.db.commit()
            raise
    
    async def bulk_enrich(
        self,
        observable_ids: List[UUID],
        max_concurrent: int = 5,
    ) -> List[Observable]:
        """
        Enrich multiple observables concurrently.
        
        Args:
            observable_ids: List of observable IDs to enrich
            max_concurrent: Maximum number of concurrent enrichments
        
        Returns:
            List of enriched observables
        """
        import asyncio
        
        # Create semaphore to limit concurrent enrichments
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enrich_with_semaphore(obs_id):
            async with semaphore:
                return await self.enrich_observable(obs_id)
        
        # Run enrichments concurrently
        tasks = [enrich_with_semaphore(obs_id) for obs_id in observable_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful results
        enriched = [r for r in results if isinstance(r, Observable)]
        return enriched

