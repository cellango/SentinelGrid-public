"""Posture Service - Core REST + GraphQL API for CSPM."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
import sys
import os
import logging

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SentinelGrid Posture Service",
    description="AI-first CSPM service with REST + GraphQL APIs",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import REST routers
from app.api.rest import posture, findings, assets

# Include REST API routes
app.include_router(posture.router, prefix="/api/v1")
app.include_router(findings.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")

# GraphQL endpoint (will be added later)
# from app.api.graphql.schema import schema
# graphql_app = GraphQLRouter(schema)
# app.include_router(graphql_app, prefix="/graphql")


@app.get("/")
def root():
    """Root endpoint with service info."""
    return {
        "service": "posture-service",
        "version": "1.0.0",
        "apis": {
            "rest": "/api/v1",
            "graphql": "/graphql (coming soon)",
            "docs": "/docs"
        }
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

