"""Compliance framework catalog endpoints."""

from fastapi import APIRouter, HTTPException

from app.services.framework_catalog import framework_catalog

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


@router.get("/frameworks")
def list_frameworks():
    """List framework catalogs available to the compliance module."""
    return framework_catalog.list_frameworks()


@router.get("/frameworks/{framework_id}/controls")
def list_framework_controls(framework_id: str):
    """List controls for a framework catalog."""
    payload = framework_catalog.list_controls(framework_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Compliance framework not found")
    return payload


@router.get("/frameworks/{framework_id}")
def get_framework(framework_id: str):
    """Get framework catalog metadata and categories."""
    payload = framework_catalog.get_framework(framework_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Compliance framework not found")
    return payload

