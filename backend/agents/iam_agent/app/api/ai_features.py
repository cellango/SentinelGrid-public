"""AI Features API endpoints (Anomaly Detection, Risk Scoring, Recommendations)."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional

from app.api.request_context import RequestContext, get_current_request_context
from app.models.ai_features import (
    AnomalyDetectionRequest,
    AnomalyResponse,
    RiskScoreRequest,
    RiskScoreResponse,
    RecommendationRequest,
    RecommendationResponse
)
from app.services.keycloak_client import KeycloakClient
from app.services.anomaly_detection import AnomalyDetectionService
from app.services.risk_scoring import RiskScoringService
from app.services.recommendation_engine import RecommendationEngine
from app.api.auth import get_keycloak_client

router = APIRouter(prefix="/internal/iam/ai", tags=["ai-features"])


def _resolve_tenant_id(
    request_context: RequestContext,
    requested_tenant_id: Optional[str] = None,
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if requested_tenant_id is not None and requested_tenant_id != authenticated_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


def get_anomaly_service() -> AnomalyDetectionService:
    """Get anomaly detection service instance."""
    return AnomalyDetectionService()


def get_risk_service() -> RiskScoringService:
    """Get risk scoring service instance."""
    return RiskScoringService()


def get_recommendation_engine() -> RecommendationEngine:
    """Get recommendation engine instance."""
    return RecommendationEngine()


@router.post("/anomalies/detect", response_model=AnomalyResponse)
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service),
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> AnomalyResponse:
    """Detect anomalies in user access patterns."""
    try:
        tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        anomalies = []
        
        if request.user_id:
            # Get user access history (mock for now - would fetch from audit logs)
            access_history = []  # TODO: Fetch from audit logs/access logs
            
            user_anomalies = anomaly_service.detect_access_pattern_anomalies(
                request.user_id,
                access_history,
                request.tenant_id
            )
            anomalies.extend(user_anomalies)
        else:
            # Detect for all users or tenant
            users = keycloak_client.list_users()
            for user in users[:100]:  # Limit to first 100
                user_id = user.get("id")
                if user_id:
                    access_history = []  # TODO: Fetch from audit logs
                    user_anomalies = anomaly_service.detect_access_pattern_anomalies(
                        user_id,
                        access_history,
                        tenant_id
                    )
                    anomalies.extend(user_anomalies)
        
        # Count by severity
        critical_count = sum(1 for a in anomalies if a.get("severity") == "critical")
        high_count = sum(1 for a in anomalies if a.get("severity") == "high")
        medium_count = sum(1 for a in anomalies if a.get("severity") == "medium")
        
        return AnomalyResponse(
            user_id=request.user_id,
            tenant_id=tenant_id,
            anomalies=anomalies,
            total_count=len(anomalies),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting anomalies: {str(e)}")


@router.post("/risk/score", response_model=RiskScoreResponse)
async def calculate_risk_score(
    request: RiskScoreRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    risk_service: RiskScoringService = Depends(get_risk_service),
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> RiskScoreResponse:
    """Calculate risk score for user, entitlement, resource, or tenant."""
    try:
        tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        if request.scope == "user" and request.user_id:
            # Get user data
            user = keycloak_client.get_user(request.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            user_data = {
                "roles": keycloak_client.get_user_roles(request.user_id),
                "entitlements": []  # TODO: Fetch from Entitlement Agent
            }
            
            access_history = []  # TODO: Fetch from audit logs
            anomalies = []  # TODO: Get from anomaly detection
            
            result = risk_service.calculate_user_risk_score(
                request.user_id,
                user_data,
                access_history,
                anomalies,
                tenant_id
            )
            
            return RiskScoreResponse(**result)
            
        elif request.scope == "tenant":
            users = []  # TODO: Get users for tenant
            entitlements = []  # TODO: Get entitlements for tenant
            anomalies = []  # TODO: Get anomalies for tenant
            
            result = risk_service.calculate_tenant_risk_score(
                tenant_id,
                users,
                entitlements,
                anomalies
            )
            
            return RiskScoreResponse(
                scope="tenant",
                entity_id=tenant_id,
                **result
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid scope or missing ID")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating risk score: {str(e)}")


@router.get("/risk/users", response_model=List[RiskScoreResponse])
async def list_user_risk_scores(
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    request_context: RequestContext = Depends(get_current_request_context),
    keycloak_client: KeycloakClient = Depends(get_keycloak_client),
    risk_service: RiskScoringService = Depends(get_risk_service)
) -> List[RiskScoreResponse]:
    """List risk scores for multiple users."""
    try:
        resolved_tenant_id = _resolve_tenant_id(request_context, tenant_id)
        users = keycloak_client.list_users()
        
        # Filter by tenant if provided
        # TODO: Implement tenant filtering
        
        risk_scores = []
        for user in users[:limit]:
            user_id = user.get("id")
            if user_id:
                user_data = {
                    "roles": keycloak_client.get_user_roles(user_id),
                    "entitlements": []
                }
                
                access_history = []
                anomalies = []
                
                result = risk_service.calculate_user_risk_score(
                    user_id,
                    user_data,
                    access_history,
                    anomalies,
                    resolved_tenant_id
                )
                
                risk_scores.append(RiskScoreResponse(**result))
        
        # Sort by risk score (highest first)
        risk_scores.sort(key=lambda x: x.overall_risk_score, reverse=True)
        
        return risk_scores
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating risk scores: {str(e)}")


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    recommendation_engine: RecommendationEngine = Depends(get_recommendation_engine),
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> RecommendationResponse:
    """Get AI-powered recommendations."""
    try:
        tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        recommendations = []
        
        if request.type == "role_mining" or request.type is None:
            users = keycloak_client.list_users()
            entitlements = []  # TODO: Get from Entitlement Agent
            
            role_recommendations = recommendation_engine.recommend_role_mining(
                users,
                entitlements,
                tenant_id
            )
            recommendations.extend(role_recommendations)
        
        if request.type == "optimization" or request.type is None:
            users = keycloak_client.list_users()
            access_history = []  # TODO: Get from audit logs
            
            opt_recommendations = recommendation_engine.recommend_access_optimization(
                users,
                access_history,
                tenant_id
            )
            recommendations.extend(opt_recommendations)
        
        if request.type == "compliance" or request.type is None:
            if tenant_id:
                users = keycloak_client.list_users()
                policies = keycloak_client.get_authorization_policies()
                entitlements = []
                
                compliance_recommendations = recommendation_engine.recommend_compliance_improvements(
                    tenant_id,
                    policies,
                    users,
                    entitlements
                )
                recommendations.extend(compliance_recommendations)
        
        if request.type == "ai" and request.query:
            context = request.context or {}
            ai_recommendations = recommendation_engine.generate_ai_recommendations(
                request.query,
                context,
                tenant_id
            )
            recommendations.append(ai_recommendations)
        
        high_priority_count = sum(1 for r in recommendations if r.get("priority") in ["high", "critical"])
        
        return RecommendationResponse(
            recommendations=recommendations,
            total_count=len(recommendations),
            high_priority_count=high_priority_count
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.get("/recommendations/compliance")
async def get_compliance_recommendations(
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    recommendation_engine: RecommendationEngine = Depends(get_recommendation_engine),
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> RecommendationResponse:
    """Get compliance-specific recommendations."""
    try:
        resolved_tenant_id = _resolve_tenant_id(request_context, tenant_id)
        users = keycloak_client.list_users()
        policies = keycloak_client.get_authorization_policies()
        entitlements = []
        
        recommendations = recommendation_engine.recommend_compliance_improvements(
            resolved_tenant_id,
            policies,
            users,
            entitlements
        )
        
        high_priority_count = sum(1 for r in recommendations if r.get("priority") in ["high", "critical"])
        
        return RecommendationResponse(
            recommendations=recommendations,
            total_count=len(recommendations),
            high_priority_count=high_priority_count
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating compliance recommendations: {str(e)}")
