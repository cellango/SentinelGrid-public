from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.core.security import enforce_org_scope, get_internal_org_id, require_internal_service_token
from app import models

router = APIRouter()

@router.get("/config/{org_id}")
def get_gateway_config(
    org_id: str,
    _: str = Depends(require_internal_service_token),
    current_org_id = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """
    Export gateway configuration for an organization
    Returns apps and policies for gateway to cache
    """
    org_id = str(enforce_org_scope(current_org_id, org_id))
    # Get all apps for org
    apps = db.query(models.AiApp).filter(models.AiApp.org_id == org_id).all()
    
    # Get all policies for org (org-wide + per-app)
    policies = db.query(models.AiPolicy).filter(models.AiPolicy.org_id == org_id).all()
    
    # Build config structure
    config = {
        "org_id": org_id,
        "apps": [],
        "policies": {
            "org_default": None,
            "per_app": {}
        }
    }
    
    # Add apps
    for app in apps:
        config["apps"].append({
            "id": str(app.id),
            "name": app.name,
            "environment": app.environment,
            "allowed_models": app.allowed_models or [],
            "allow_external_providers": app.allow_external_providers,
            "max_context_tokens": app.max_context_tokens
        })
    
    # Add policies
    for policy in policies:
        policy_data = {
            "block_pii_outbound": policy.block_pii_outbound,
            "block_secrets_outbound": policy.block_secrets_outbound,
            "block_external_llms": policy.block_external_llms,
            "block_jailbreak_patterns": policy.block_jailbreak_patterns,
            "require_approval_for_high_risk_tools": policy.require_approval_for_high_risk_tools
        }
        
        if policy.ai_app_id is None:
            # Org-wide default
            config["policies"]["org_default"] = policy_data
        else:
            # Per-app policy
            config["policies"]["per_app"][str(policy.ai_app_id)] = policy_data
    
    return config
