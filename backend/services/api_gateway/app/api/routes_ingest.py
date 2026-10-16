"""Proxy endpoints for ingestion metadata and pipeline testing (OpenSearch)."""

import os
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/ingest", tags=["ingest"])

OS_URL = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
OS_USER = os.getenv("OPENSEARCH_USERNAME")
OS_PASS = os.getenv("OPENSEARCH_PASSWORD")


def _http_client():
    auth = None
    if OS_USER and OS_PASS:
        auth = (OS_USER, OS_PASS)
    return httpx.AsyncClient(base_url=OS_URL, auth=auth, timeout=10.0)


def _build_simulate_payload(event: dict) -> dict:
    # Shared diagnostic surface: this endpoint simulates platform ingest pipelines
    # against caller-provided sample events and intentionally does not derive tenant scope.
    return {"docs": [{"_source": event}]}


@router.get("/pipelines")
async def list_pipelines():
    try:
        async with _http_client() as client:
            resp = await client.get("/_ingest/pipeline")
            resp.raise_for_status()
            data = resp.json()
            pipelines = [{"name": name, "description": val.get("description")} for name, val in data.items()]
            return {"pipelines": pipelines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pipelines: {e}")


@router.get("/templates")
async def list_templates():
    try:
        async with _http_client() as client:
            resp = await client.get("/_index_template")
            resp.raise_for_status()
            data = resp.json()
            templates = []
            for tpl in data.get("index_templates", []):
                name = tpl.get("name")
                body = tpl.get("index_template", {})
                templates.append(
                    {
                        "name": name,
                        "index_patterns": body.get("index_patterns", []),
                        "priority": body.get("priority"),
                    }
                )
            return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch templates: {e}")


@router.post("/test-pipeline")
async def test_pipeline(payload: dict):
    """
    Run a sample document through a specified ingest pipeline.
    This is an approved shared diagnostic surface for platform pipeline testing.
    payload: { "pipeline": "pipeline-name", "event": { ... } }
    """
    pipeline = payload.get("pipeline")
    event = payload.get("event")
    if not pipeline or not event:
        raise HTTPException(status_code=400, detail="pipeline and event are required")
    try:
        async with _http_client() as client:
            resp = await client.post(f"/_ingest/pipeline/{pipeline}/_simulate", json=_build_simulate_payload(event))
            resp.raise_for_status()
            data = resp.json()
            return data.get("docs", [{}])[0].get("doc", {}).get("_source", {})
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test pipeline: {e}")
