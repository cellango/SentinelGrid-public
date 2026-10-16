"""
Provider Credentials API

Manages configuration for how the AI Shield gateway accesses customer-controlled
AI provider API keys. Keys are NEVER stored here - only vault references.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import logging

from app.core.database import get_db
from app.models import AiProviderCredential
from app.schemas import (
    ProviderCredentialSetup,
    ProviderCredentialResponse,
    ProviderCredentialUpdate,
    VaultValidationResponse
)
from app.services.vault_delegation import VaultDelegationService, VaultAccessError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/provider-credentials", tags=["provider-credentials"])

# Initialize vault service
vault_service = VaultDelegationService()


@router.post("/setup", response_model=ProviderCredentialResponse, status_code=status.HTTP_201_CREATED)
async def setup_provider_credentials(
    config: ProviderCredentialSetup,
    db: Session = Depends(get_db)
):
    """
    Configure how gateway accesses customer's provider API key.
    
    This endpoint sets up the connection to customer's vault but does NOT
    store the actual API key. Gateway will fetch keys on-demand.
    
    Supports:
    - Vault Delegation: Customer grants read-only IAM role
    - Customer Proxy: Customer runs key-holder sidecar
    - Dual-Key: Separate gateway key vs emergency key
    """
    try:
        # Validate the configuration by attempting to fetch the key
        logger.info(f"Validating vault access for org {config.org_id}, provider {config.provider}")
        
        if config.access_method == "vault-delegation":
            # Test vault access
            success, error = await vault_service.validate_vault_access({
                'vault_type': config.vault_type,
                'vault_secret_path': config.vault_secret_path,
                'iam_role_arn': config.iam_role_arn,
                'vault_region': config.vault_region
            })
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vault validation failed: {error}"
                )
        
        # Check if config already exists
        existing = db.query(AiProviderCredential).filter(
            and_(
                AiProviderCredential.org_id == config.org_id,
                AiProviderCredential.provider == config.provider
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Configuration for {config.provider} already exists. Use PUT to update."
            )
        
        # Create new credential configuration
        credential = AiProviderCredential(
            org_id=config.org_id,
            provider=config.provider,
            deployment_model=config.deployment_model,
            access_method=config.access_method,
            vault_type=config.vault_type,
            vault_secret_path=config.vault_secret_path,
            iam_role_arn=config.iam_role_arn,
            vault_region=config.vault_region,
            proxy_endpoint_url=config.proxy_endpoint_url,
            proxy_auth_token_hash=config.proxy_auth_token_hash,
            gateway_key_fingerprint=config.gateway_key_fingerprint,
            is_active=True,
            last_validated=datetime.utcnow(),
            created_by=config.created_by
        )
        
        db.add(credential)
        db.commit()
        db.refresh(credential)
        
        logger.info(f"Created provider credential config: {credential.id}")
        
        return ProviderCredentialResponse.from_orm(credential)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up provider credentials: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup provider credentials: {str(e)}"
        )


@router.get("", response_model=List[ProviderCredentialResponse])
async def list_provider_credentials(
    org_id: UUID,
    provider: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    List provider credential configurations for an organization.
    Returns metadata only - never actual API keys.
    """
    query = db.query(AiProviderCredential).filter(AiProviderCredential.org_id == org_id)
    
    if provider:
        query = query.filter(AiProviderCredential.provider == provider)
    
    if active_only:
        query = query.filter(AiProviderCredential.is_active == True)
    
    credentials = query.all()
    return [ProviderCredentialResponse.from_orm(c) for c in credentials]


@router.get("/{credential_id}", response_model=ProviderCredentialResponse)
async def get_provider_credential(
    credential_id: UUID,
    db: Session = Depends(get_db)
):
    """Get specific provider credential configuration by ID"""
    credential = db.query(AiProviderCredential).filter(
        AiProviderCredential.id == credential_id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential configuration {credential_id} not found"
        )
    
    return ProviderCredentialResponse.from_orm(credential)


@router.put("/{credential_id}", response_model=ProviderCredentialResponse)
async def update_provider_credential(
    credential_id: UUID,
    update: ProviderCredentialUpdate,
    db: Session = Depends(get_db)
):
    """Update provider credential configuration"""
    credential = db.query(AiProviderCredential).filter(
        AiProviderCredential.id == credential_id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential configuration {credential_id} not found"
        )
    
    try:
        # Update fields if provided
        if update.vault_secret_path is not None:
            credential.vault_secret_path = update.vault_secret_path
        if update.iam_role_arn is not None:
            credential.iam_role_arn = update.iam_role_arn
        if update.vault_region is not None:
            credential.vault_region = update.vault_region
        if update.proxy_endpoint_url is not None:
            credential.proxy_endpoint_url = update.proxy_endpoint_url
        if update.is_active is not None:
            credential.is_active = update.is_active
        
        credential.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(credential)
        
        logger.info(f"Updated provider credential: {credential_id}")
        return ProviderCredentialResponse.from_orm(credential)
        
    except Exception as e:
        logger.error(f"Error updating credential: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update credential: {str(e)}"
        )


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_credential(
    credential_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete provider credential configuration"""
    credential = db.query(AiProviderCredential).filter(
        AiProviderCredential.id == credential_id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential configuration {credential_id} not found"
        )
    
    try:
        db.delete(credential)
        db.commit()
        logger.info(f"Deleted provider credential: {credential_id}")
        
    except Exception as e:
        logger.error(f"Error deleting credential: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete credential: {str(e)}"
        )


@router.post("/test", response_model=VaultValidationResponse)
async def test_provider_access(
    org_id: UUID,
    provider: str,
    db: Session = Depends(get_db)
):
    """
    Test if gateway can successfully fetch customer's provider key.
    
    Attempts to:
    1. Find credential configuration
    2. Connect to customer's vault
    3. Fetch the key
    4. Make a test API call to the provider (if requested)
    
    Does NOT return the actual key - only validation status.
    """
    # Find the credential configuration
    credential = db.query(AiProviderCredential).filter(
        and_(
            AiProviderCredential.org_id == org_id,
            AiProviderCredential.provider == provider,
            AiProviderCredential.is_active == True
        )
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active configuration found for {provider}"
        )
    
    try:
        # Build config dict for vault service
        config = {
            'vault_type': credential.vault_type,
            'vault_secret_path': credential.vault_secret_path,
            'iam_role_arn': credential.iam_role_arn,
            'vault_region': credential.vault_region
        }
        
        # Attempt to fetch the key
        logger.info(f"Testing vault access for org {org_id}, provider {provider}")
        api_key = await vault_service.fetch_provider_key(
            org_id=str(org_id),
            provider=provider,
            credential_config=config
        )
        
        # Update last validated timestamp
        credential.last_validated = datetime.utcnow()
        credential.validation_error = None
        db.commit()
        
        # Generate key fingerprint for verification (not security)
        import hashlib
        fingerprint = hashlib.sha256(api_key[:8].encode()).hexdigest()[:16]
        
        logger.info(f"Vault access test successful for {org_id}/{provider}")
        
        return VaultValidationResponse(
            success=True,
            message="Successfully fetched provider key from vault",
            key_fingerprint=fingerprint,
            timestamp=datetime.utcnow()
        )
        
    except VaultAccessError as e:
        # Update validation error
        credential.validation_error = str(e)
        db.commit()
        
        logger.warning(f"Vault access test failed: {str(e)}")
        
        return VaultValidationResponse(
            success=False,
            message=f"Vault access failed: {str(e)}",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error testing vault access: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test failed: {str(e)}"
        )


@router.post("/{credential_id}/rotate-proxy-token", response_model=ProviderCredentialResponse)
async def rotate_proxy_token(
    credential_id: UUID,
    new_token_hash: str,
    db: Session = Depends(get_db)
):
    """
    Rotate the authentication token for customer-proxy access method.
    Requires the new token hash (SHA-256).
    """
    credential = db.query(AiProviderCredential).filter(
        AiProviderCredential.id == credential_id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential configuration {credential_id} not found"
        )
    
    if credential.access_method != "customer-proxy":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token rotation only applies to customer-proxy access method"
        )
    
    try:
        credential.proxy_auth_token_hash = new_token_hash
        credential.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(credential)
        
        logger.info(f"Rotated proxy token for credential: {credential_id}")
        return ProviderCredentialResponse.from_orm(credential)
        
    except Exception as e:
        logger.error(f"Error rotating token: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rotate token: {str(e)}"
        )

