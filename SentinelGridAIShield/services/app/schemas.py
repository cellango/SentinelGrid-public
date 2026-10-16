from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator
from typing import Optional, List, Union, Dict, Any
from uuid import UUID
from datetime import datetime


# ============ AI Apps ============

class AiAppCreate(BaseModel):
    org_id: UUID
    name: str
    environment: str
    description: Optional[str] = None
    allowed_models: Optional[List[str]] = None
    allow_external_providers: bool = True
    max_context_tokens: int = 100000


class AiAppResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    environment: str
    description: Optional[str]
    allowed_models: Optional[List[str]]
    allow_external_providers: bool
    max_context_tokens: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AiAppWithKey(AiAppResponse):
    api_key: str


class AiAppUpdate(BaseModel):
    name: Optional[str] = None
    environment: Optional[str] = None
    description: Optional[str] = None
    allowed_models: Optional[List[str]] = None
    allow_external_providers: Optional[bool] = None
    max_context_tokens: Optional[int] = None


# ============ AI Policies ============

class AiPolicyCreate(BaseModel):
    org_id: UUID
    ai_app_id: Optional[UUID] = None
    block_pii_outbound: bool = False
    block_secrets_outbound: bool = True
    block_external_llms: bool = False
    block_jailbreak_patterns: bool = True
    require_approval_for_high_risk_tools: bool = True


class AiPolicyResponse(BaseModel):
    id: UUID
    org_id: UUID
    ai_app_id: Optional[UUID]
    block_pii_outbound: bool
    block_secrets_outbound: bool
    block_external_llms: bool
    block_jailbreak_patterns: bool
    require_approval_for_high_risk_tools: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AiPolicyUpdate(BaseModel):
    ai_app_id: Optional[UUID] = None
    block_pii_outbound: Optional[bool] = None
    block_secrets_outbound: Optional[bool] = None
    block_external_llms: Optional[bool] = None
    block_jailbreak_patterns: Optional[bool] = None
    require_approval_for_high_risk_tools: Optional[bool] = None


# ============ AI Events ============

class AiEventResponse(BaseModel):
    id: UUID
    org_id: UUID
    ai_app_id: Optional[UUID]
    user_id: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    has_pii: bool
    has_secrets: bool
    prompt_injection_suspected: bool
    policy_decision: Optional[str]
    tokens_in: Optional[int]
    tokens_out: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None


# ============ Guardrails ============

class PIIScanRequest(BaseModel):
    text: str


class PIIScanResponse(BaseModel):
    has_pii: bool
    entities: List[str]
    redacted: str


class InjectionScanRequest(BaseModel):
    text: str


class InjectionScanResponse(BaseModel):
    is_suspicious: bool
    score: float
    patterns: List[str]


class SecretsScanRequest(BaseModel):
    text: str


class SecretsScanResponse(BaseModel):
    has_secrets: bool
    findings: List[str]


class TelemetryEventCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("event_id", "id"),
    )
    org_id: UUID = Field(validation_alias=AliasChoices("org_id", "tenant_id"))
    ai_app_id: Optional[Union[UUID, str]] = Field(
        default=None,
        validation_alias=AliasChoices("ai_app_id", "app_id"),
    )
    realm: Optional[str] = None
    user_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    has_pii: bool = False
    has_secrets: bool = False
    prompt_injection_suspected: bool = False
    policy_decision: Optional[str] = None
    violation_reason: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    prompt_preview: Optional[str] = None
    response_preview: Optional[str] = None
    created_at: Optional[datetime] = None

    @model_validator(mode="after")
    def normalize_ai_app_id(self) -> "TelemetryEventCreate":
        if self.ai_app_id == "default":
            self.ai_app_id = None
        return self


# ============ Provider Credentials ============

class ProviderCredentialSetup(BaseModel):
    """Configuration for how gateway accesses customer's provider key"""
    org_id: UUID
    provider: str = Field(..., description="Provider name: openai, anthropic, azure-openai, local")
    deployment_model: str = Field(..., description="Deployment model: self-hosted or saas")
    access_method: str = Field(..., description="Access method: vault-delegation, customer-proxy, or dual-key")
    
    # Vault delegation fields
    vault_type: Optional[str] = Field(None, description="Vault type: aws-secrets, azure-keyvault, hashicorp-vault")
    vault_secret_path: Optional[str] = Field(None, description="Path to secret in vault")
    iam_role_arn: Optional[str] = Field(None, description="IAM role ARN or service principal ID")
    vault_region: Optional[str] = Field(None, description="Vault region (AWS region, Azure location, etc)")
    
    # Customer proxy fields
    proxy_endpoint_url: Optional[str] = Field(None, description="URL to customer's key proxy")
    proxy_auth_token_hash: Optional[str] = Field(None, description="Hashed authentication token")
    
    # Dual-key fields
    gateway_key_fingerprint: Optional[str] = Field(None, description="Fingerprint of gateway key")
    
    # Metadata
    created_by: Optional[str] = Field(None, description="User who created this config")

    class Config:
        json_schema_extra = {
            "example": {
                "org_id": "123e4567-e89b-12d3-a456-426614174000",
                "provider": "openai",
                "deployment_model": "saas",
                "access_method": "vault-delegation",
                "vault_type": "aws-secrets",
                "vault_secret_path": "sentinelgrid/openai-key",
                "iam_role_arn": "arn:aws:iam::123456789012:role/SentinelGridGatewayAccess",
                "vault_region": "us-east-1"
            }
        }


class ProviderCredentialUpdate(BaseModel):
    """Update provider credential configuration"""
    vault_secret_path: Optional[str] = None
    iam_role_arn: Optional[str] = None
    vault_region: Optional[str] = None
    proxy_endpoint_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProviderCredentialResponse(BaseModel):
    """Provider credential configuration (never includes actual keys)"""
    id: UUID
    org_id: UUID
    provider: str
    deployment_model: str
    access_method: str
    vault_type: Optional[str]
    vault_secret_path: Optional[str]
    iam_role_arn: Optional[str]
    vault_region: Optional[str]
    proxy_endpoint_url: Optional[str]
    gateway_key_fingerprint: Optional[str]
    is_active: bool
    last_validated: Optional[datetime]
    validation_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VaultValidationResponse(BaseModel):
    """Response from vault validation test"""
    success: bool
    message: str
    key_fingerprint: Optional[str] = Field(None, description="First 16 chars of key SHA-256 hash for verification")
    timestamp: datetime
