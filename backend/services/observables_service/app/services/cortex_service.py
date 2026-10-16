"""Cortex API client for observable enrichment."""

import logging
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class CortexService:
    """Service for interacting with Cortex API."""
    
    def __init__(self):
        self.base_url = settings.CORTEX_URL
        self.api_key = settings.CORTEX_API_KEY
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    async def create_observable(
        self,
        data_type: str,
        data: str,
        tlp: int = 2,
        tags: Optional[List[str]] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an observable in Cortex.
        
        Args:
            data_type: Type of observable (ip, domain, url, hash, etc.)
            data: The actual data
            tlp: TLP level (0-3)
            tags: Optional tags
            message: Optional message
        
        Returns:
            Observable object from Cortex
        """
        if not self.base_url:
            logger.warning("Cortex URL not configured, returning mock observable")
            return {
                "id": "mock-observable-1",
                "dataType": data_type,
                "data": data,
                "tlp": tlp,
                "tags": tags or [],
            }
        
        try:
            observable_data = {
                "dataType": data_type,
                "data": data,
                "tlp": tlp,
                "tags": tags or [],
            }
            if message:
                observable_data["message"] = message
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/observable"
                response = await client.post(url, json=observable_data, headers=self.headers)
                response.raise_for_status()
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Failed to create observable in Cortex: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Cortex API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def list_analyzers(self, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available analyzers in Cortex.
        
        Args:
            data_type: Optional filter by observable data type
        
        Returns:
            List of analyzer definitions
        """
        if not self.base_url:
            logger.warning("Cortex URL not configured, returning mock analyzers")
            return [
                {
                    "id": "VirusTotal_GetReport_3_0",
                    "name": "VirusTotal",
                    "dataTypeList": ["hash", "ip", "domain", "url"]
                },
                {
                    "id": "AbuseIPDB_1_0",
                    "name": "AbuseIPDB",
                    "dataTypeList": ["ip"]
                },
                {
                    "id": "PassiveDNS_2_0",
                    "name": "PassiveDNS",
                    "dataTypeList": ["domain", "ip"]
                },
                {
                    "id": "SentinelGrid_UserInfo_1_0",
                    "name": "SentinelGrid User Info",
                    "dataTypeList": ["user_id"]
                },
            ]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/analyzer"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                analyzers = response.json()
                
                # Filter by data type if specified
                if data_type:
                    analyzers = [
                        a for a in analyzers
                        if data_type in a.get("dataTypeList", [])
                    ]
                
                return analyzers
        
        except httpx.RequestError as e:
            logger.error(f"Failed to list analyzers from Cortex: {e}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"Cortex API error: {e.response.status_code} - {e.response.text}")
            return []
    
    async def run_analyzer(
        self,
        analyzer_id: str,
        observable_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run an analyzer on an observable.
        
        Args:
            analyzer_id: Cortex analyzer ID
            observable_id: Cortex observable ID
            parameters: Optional analyzer parameters
        
        Returns:
            Analyzer job response with job_id
        """
        if not self.base_url:
            logger.warning("Cortex URL not configured, returning mock analyzer job")
            return {
                "id": "mock-job-1",
                "analyzerId": analyzer_id,
                "artifactId": observable_id,
                "status": "Success",
                "report": {
                    "full": {"verdict": "clean", "summary": "Mock analyzer result"}
                }
            }
        
        try:
            job_data = {
                "analyzerId": analyzer_id,
                "artifactId": observable_id,
            }
            if parameters:
                job_data["parameters"] = parameters
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/analyzer/{analyzer_id}/run"
                response = await client.post(url, json=job_data, headers=self.headers)
                response.raise_for_status()
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Failed to run analyzer in Cortex: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Cortex API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def get_job_report(self, job_id: str) -> Dict[str, Any]:
        """
        Get analyzer job status and results.
        
        Args:
            job_id: Analyzer job ID
        
        Returns:
            Job status and report
        """
        if not self.base_url:
            logger.warning("Cortex URL not configured, returning mock job status")
            return {
                "id": job_id,
                "status": "Success",
                "report": {
                    "full": {"verdict": "clean", "summary": "Mock analyzer result"}
                }
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/job/{job_id}"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"Failed to get job report from Cortex: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Cortex API error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def wait_for_job(self, job_id: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for analyzer job to complete.
        
        Args:
            job_id: Job ID to wait for
            timeout: Maximum time to wait in seconds
        
        Returns:
            Completed job report
        """
        import asyncio
        
        elapsed = 0
        interval = 5
        
        while elapsed < timeout:
            report = await self.get_job_report(job_id)
            status = report.get("status")
            
            if status in ["Success", "Failure"]:
                return report
            
            await asyncio.sleep(interval)
            elapsed += interval
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

