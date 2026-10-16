"""Enrollment protocol endpoints (ACME, SCEP, EST)."""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_tenant
from app.core.config import settings
from app.providers.enrollment import ACMEProvider, SCEPProvider, ESTProvider

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/v1/enrollment/acme/directory")
async def get_acme_directory(
    tenant_id: UUID = Depends(get_current_tenant),
    alias: Optional[str] = Query(None, description="ACME alias name")
):
    """
    Get ACME directory endpoint information.
    
    Returns ACME directory URL and endpoints for certificate enrollment.
    """
    try:
        provider = ACMEProvider(
            ejbca_url=settings.EJBCA_URL,
            ejbca_username=settings.EJBCA_USERNAME,
            ejbca_password=settings.EJBCA_PASSWORD,
            alias=alias or settings.EJBCA_ACME_ALIAS,
            verify_ssl=settings.EJBCA_VERIFY_SSL
        )
        
        directory_url = provider.get_directory_url()
        
        return {
            "directory_url": directory_url,
            "new_account_url": provider.get_account_url(),
            "new_order_url": provider.get_new_order_url(),
            "new_nonce_url": f"{directory_url.rstrip('/directory')}/newNonce",
            "key_change_url": f"{directory_url.rstrip('/directory')}/keyChange",
            "revoke_cert_url": f"{directory_url.rstrip('/directory')}/revokeCert",
            "meta": {
                "terms_of_service": f"{directory_url.rstrip('/directory')}/terms",
                "website": settings.EJBCA_URL,
                "caa_identities": []
            }
        }
    except Exception as e:
        logger.error(f"Error getting ACME directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/enrollment/scep/endpoint")
async def get_scep_endpoint(
    tenant_id: UUID = Depends(get_current_tenant),
    ra_name: Optional[str] = Query(None, description="SCEP RA name")
):
    """
    Get SCEP endpoint information.
    
    Returns SCEP endpoint URL and CA certificate URL.
    """
    try:
        provider = SCEPProvider(
            ejbca_url=settings.EJBCA_URL,
            ejbca_username=settings.EJBCA_USERNAME,
            ejbca_password=settings.EJBCA_PASSWORD,
            ra_name=ra_name or settings.EJBCA_SCEP_RA_NAME,
            verify_ssl=settings.EJBCA_VERIFY_SSL
        )
        
        return {
            "scep_endpoint_url": provider.get_scep_endpoint_url(),
            "ca_certificate_url": provider.get_ca_certificate_url(),
            "instructions": {
                "description": "SCEP enrollment for network devices",
                "usage": "Use SCEP client to connect to endpoint URL",
                "password": "SCEP password required (configured in EJBCA)"
            }
        }
    except Exception as e:
        logger.error(f"Error getting SCEP endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/enrollment/est/cacerts")
async def get_est_cacerts(
    tenant_id: UUID = Depends(get_current_tenant),
    alias: Optional[str] = Query(None, description="EST alias name")
):
    """
    Get EST CA certificates endpoint.
    
    Returns EST CA certificates URL.
    """
    try:
        provider = ESTProvider(
            ejbca_url=settings.EJBCA_URL,
            ejbca_username=settings.EJBCA_USERNAME,
            ejbca_password=settings.EJBCA_PASSWORD,
            alias=alias or settings.EJBCA_EST_ALIAS,
            verify_ssl=settings.EJBCA_VERIFY_SSL
        )
        
        return {
            "cacerts_url": provider.get_cacerts_url(),
            "simpleenroll_url": provider.get_simpleenroll_url(),
            "simplereenroll_url": provider.get_simplereenroll_url(),
            "instructions": {
                "description": "EST enrollment for modern devices",
                "usage": "Use EST client to connect to endpoints",
                "authentication": "Client certificate or username/password"
            }
        }
    except Exception as e:
        logger.error(f"Error getting EST endpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/enrollment/protocols")
async def list_enrollment_protocols(
    tenant_id: UUID = Depends(get_current_tenant)
):
    """
    List all available enrollment protocols and their endpoints.
    
    Returns information about ACME, SCEP, and EST protocols.
    """
    try:
        return {
            "protocols": {
                "acme": {
                    "name": "ACME (Automatic Certificate Management Environment)",
                    "version": "ACME v2",
                    "directory_url": f"{settings.EJBCA_URL}/ejbca/acme/directory",
                    "use_cases": [
                        "Web servers (certbot, acme.sh)",
                        "Kubernetes (cert-manager)",
                        "Automated certificate renewal"
                    ],
                    "endpoint": "/v1/enrollment/acme/directory"
                },
                "scep": {
                    "name": "SCEP (Simple Certificate Enrollment Protocol)",
                    "version": "SCEP v1",
                    "endpoint_url": f"{settings.EJBCA_URL}/ejbca/publicweb/apply/scep/pkiclient.exe",
                    "use_cases": [
                        "Network devices (routers, firewalls)",
                        "Legacy devices",
                        "Windows devices"
                    ],
                    "endpoint": "/v1/enrollment/scep/endpoint"
                },
                "est": {
                    "name": "EST (Enrollment over Secure Transport)",
                    "version": "EST v1.0",
                    "cacerts_url": f"{settings.EJBCA_URL}/.well-known/est/cacerts",
                    "use_cases": [
                        "Modern network devices",
                        "IoT devices",
                        "Mobile device management"
                    ],
                    "endpoint": "/v1/enrollment/est/cacerts"
                }
            }
        }
    except Exception as e:
        logger.error(f"Error listing enrollment protocols: {e}")
        raise HTTPException(status_code=500, detail=str(e))

