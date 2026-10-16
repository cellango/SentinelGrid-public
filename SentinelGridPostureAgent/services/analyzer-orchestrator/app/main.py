"""Analyzer Orchestrator Service - orchestrates security analyzers."""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import asyncio
import httpx
import os
import sys
import logging

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from analyzers.registry import registry
from analyzers.base_analyzer import BaseAnalyzer

# Import and register analyzers
from analyzers.cloud.prowler_analyzer import ProwlerAWSAnalyzer
from analyzers.webapp.zap_analyzer import ZAPAnalyzer
from analyzers.container.trivy_analyzer import TrivyAnalyzer
from analyzers.iac.checkov_analyzer import CheckovAnalyzer
from analyzers.secrets.gitleaks_analyzer import GitleaksAnalyzer

# Register analyzers
registry.register(ProwlerAWSAnalyzer)
registry.register(ZAPAnalyzer)
registry.register(TrivyAnalyzer)
registry.register(CheckovAnalyzer)
registry.register(GitleaksAnalyzer)

# Configuration
POSTURE_SERVICE_URL = os.getenv("POSTURE_SERVICE_URL", "http://posture-service:8000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Analyzer Orchestrator",
    description="Orchestrates security analyzers for observable analysis",
    version="1.0.0"
)

# In-memory job store (TODO: Use Redis for production)
jobs_store: Dict[str, Dict] = {}


class AnalyzeRequest(BaseModel):
    """Request to analyze an observable."""
    tenant_id: str
    observable_type: str
    observable_value: str
    metadata: Optional[Dict[str, Any]] = None
    analyzer_tags: Optional[List[str]] = None  # Filter analyzers by tags
    analyzer_names: Optional[List[str]] = None  # Specific analyzers to run


class AnalyzeResponse(BaseModel):
    """Response from analyze request."""
    job_id: str
    observable: Dict[str, Any]
    analyzers_scheduled: List[str]
    status: str


@app.get("/")
def root():
    """Health check."""
    return {
        "service": "analyzer-orchestrator",
        "status": "healthy",
        "registered_analyzers": len(registry)
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_observable(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze an observable by running applicable analyzers.
    
    This is similar to Cortex's analyze endpoint - it:
    1. Looks up analyzers for the observable type
    2. Filters by tags if specified
    3. Runs all applicable analyzers in parallel
    4. Aggregates findings
    5. Stores them in posture-service
    """
    observable = {
        "type": request.observable_type,
        "value": request.observable_value,
        "metadata": request.metadata or {}
    }
    
    # Get applicable analyzers
    if request.analyzer_names:
        # Specific analyzers requested
        analyzer_classes = []
        for name in request.analyzer_names:
            analyzer_class = registry.get_analyzer(name)
            if analyzer_class:
                analyzer_classes.append(analyzer_class)
            else:
                logger.warning(f"Analyzer {name} not found")
    else:
        # Get by observable type and tags
        analyzer_classes = registry.get_analyzers_for_observable(
            request.observable_type,
            tags=request.analyzer_tags
        )
    
    if not analyzer_classes:
        raise HTTPException(
            status_code=404,
            detail=f"No analyzers found for {request.observable_type}"
        )
    
    # Filter by should_run()
    analyzers_to_run = []
    for analyzer_class in analyzer_classes:
        analyzer = analyzer_class()
        if analyzer.should_run(observable):
            analyzers_to_run.append(analyzer)
    
    if not analyzers_to_run:
        raise HTTPException(
            status_code=404,
            detail=f"No analyzers applicable for this observable"
        )
    
    # Create job
    job_id = str(uuid.uuid4())
    jobs_store[job_id] = {
        "id": job_id,
        "tenant_id": request.tenant_id,
        "observable": observable,
        "analyzers": [a.name for a in analyzers_to_run],
        "status": "running",
        "findings_count": 0,
        "completed_analyzers": [],
        "failed_analyzers": []
    }
    
    # Run analyzers in background
    background_tasks.add_task(
        run_analyzers,
        job_id,
        request.tenant_id,
        observable,
        analyzers_to_run
    )
    
    return AnalyzeResponse(
        job_id=job_id,
        observable=observable,
        analyzers_scheduled=[a.name for a in analyzers_to_run],
        status="running"
    )


async def run_analyzers(
    job_id: str,
    tenant_id: str,
    observable: Dict[str, Any],
    analyzers: List[BaseAnalyzer]
):
    """
    Run all analyzers in parallel and aggregate results.
    
    Args:
        job_id: Job identifier
        tenant_id: Tenant ID
        observable: Observable being analyzed
        analyzers: List of analyzer instances
    """
    logger.info(f"Job {job_id}: Running {len(analyzers)} analyzers on {observable['type']}")
    
    # Run all analyzers concurrently
    tasks = [analyzer.analyze(observable) for analyzer in analyzers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Aggregate findings
    all_findings = []
    completed_analyzers = []
    failed_analyzers = []
    
    for analyzer, result in zip(analyzers, results):
        if isinstance(result, Exception):
            logger.error(f"Analyzer {analyzer.name} failed: {str(result)}")
            failed_analyzers.append({
                "name": analyzer.name,
                "error": str(result)
            })
            continue
        
        if result.get("status") == "success":
            completed_analyzers.append(analyzer.name)
            for finding in result.get("findings", []):
                # Add context
                finding["tenant_id"] = tenant_id
                finding["observable_type"] = observable["type"]
                finding["observable_value"] = observable["value"]
                finding["analyzer_job_id"] = job_id
                all_findings.append(finding)
        else:
            failed_analyzers.append({
                "name": analyzer.name,
                "error": result.get("error", "Unknown error")
            })
    
    # Store findings in posture-service
    if all_findings:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{POSTURE_SERVICE_URL}/api/v1/findings/bulk",
                    json={
                        "tenant_id": tenant_id,
                        "findings": all_findings,
                        "job_id": job_id
                    }
                )
                response.raise_for_status()
                logger.info(f"Job {job_id}: Stored {len(all_findings)} findings")
        except Exception as e:
            logger.error(f"Failed to store findings: {str(e)}")
    
    # Update job status
    jobs_store[job_id].update({
        "status": "completed",
        "findings_count": len(all_findings),
        "completed_analyzers": completed_analyzers,
        "failed_analyzers": failed_analyzers
    })
    
    logger.info(
        f"Job {job_id} completed: {len(completed_analyzers)} succeeded, "
        f"{len(failed_analyzers)} failed, {len(all_findings)} findings"
    )


@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status."""
    if job_id not in jobs_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs_store[job_id]


@app.get("/api/v1/analyzers")
async def list_analyzers(observable_type: Optional[str] = None):
    """
    List available analyzers.
    
    Args:
        observable_type: Filter by observable type
    """
    if observable_type:
        analyzers = registry.get_analyzers_for_observable(observable_type)
        return {
            "observable_type": observable_type,
            "analyzers": [
                {
                    "name": a.name,
                    "description": a.description,
                    "version": a.version,
                    "tags": a.tags
                }
                for a in analyzers
            ]
        }
    else:
        return {
            "analyzers": registry.list_analyzers(),
            "stats": registry.get_stats()
        }


@app.get("/api/v1/observable-types")
async def list_observable_types():
    """List all supported observable types."""
    return {
        "observable_types": registry.list_observable_types(),
        "count": len(registry.list_observable_types())
    }


@app.get("/api/v1/tags")
async def list_tags():
    """List all analyzer tags."""
    return {
        "tags": registry.list_tags(),
        "count": len(registry.list_tags())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

