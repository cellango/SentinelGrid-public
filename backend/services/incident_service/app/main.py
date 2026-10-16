"""Incident Service - NIST workflow and incident management."""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.nist_workflow import NISTWorkflowEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
    if origin.strip()
]
if ENVIRONMENT == "production" and (not CORS_ORIGINS or "*" in CORS_ORIGINS):
    raise RuntimeError("CORS_ORIGINS must be an explicit allowlist in production")

app = FastAPI(
    title="SentinelGrid Incident Service",
    description="NIST workflow and incident management service",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize workflow engine
workflow_engine = NISTWorkflowEngine()


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "incident-service"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "incident-service",
        "version": "0.1.0"
    }


@app.post("/api/v1/workflow/validate-transition")
def validate_transition(current_status: str, new_status: str):
    """Validate a status transition."""
    is_valid, error = workflow_engine.validate_transition(current_status, new_status)
    return {
        "valid": is_valid,
        "error": error,
        "current_status": current_status,
        "new_status": new_status
    }


@app.get("/api/v1/workflow/phase/{status}")
def get_phase(status: str):
    """Get NIST phase for a status."""
    phase = workflow_engine.get_current_phase(status)
    return {
        "status": status,
        "phase": phase.value,
        "requirements": workflow_engine.get_phase_requirements(phase)
    }


@app.get("/api/v1/workflow/transitions/{status}")
def get_allowed_transitions(status: str):
    """Get allowed transitions from a status."""
    transitions = workflow_engine.get_allowed_transitions(status)
    return {
        "status": status,
        "allowed_transitions": [t.value for t in transitions]
    }
