from sqlalchemy import Column, String, Boolean, Integer, TIMESTAMP, ARRAY, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base

class AiApp(Base):
    __tablename__ = "ai_apps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    environment = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    allowed_models = Column(ARRAY(Text), nullable=True)
    allow_external_providers = Column(Boolean, default=True)
    max_context_tokens = Column(Integer, default=100000)
    api_key_hash = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class AiPolicy(Base):
    __tablename__ = "ai_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False)
    ai_app_id = Column(UUID(as_uuid=True), ForeignKey("ai_apps.id"), nullable=True)
    block_pii_outbound = Column(Boolean, default=False)
    block_secrets_outbound = Column(Boolean, default=True)
    block_external_llms = Column(Boolean, default=False)
    block_jailbreak_patterns = Column(Boolean, default=True)
    require_approval_for_high_risk_tools = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class AiEvent(Base):
    __tablename__ = "ai_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False)
    ai_app_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(String(255), nullable=True)
    provider = Column(String(100), nullable=True)
    model = Column(String(255), nullable=True)
    has_pii = Column(Boolean, default=False)
    has_secrets = Column(Boolean, default=False)
    prompt_injection_suspected = Column(Boolean, default=False)
    policy_decision = Column(String(50), nullable=True)
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class AiProviderCredential(Base):
    """
    Configuration for accessing customer-controlled AI provider keys.
    Keys are NEVER stored here - only vault references.
    """
    __tablename__ = "ai_provider_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False)
    provider = Column(String(50), nullable=False)  # 'openai', 'anthropic', 'azure-openai'
    deployment_model = Column(String(20), nullable=False)  # 'self-hosted', 'saas'
    access_method = Column(String(30), nullable=False)  # 'vault-delegation', 'customer-proxy', 'dual-key'
    
    # For vault-delegation
    vault_type = Column(String(20), nullable=True)  # 'aws-secrets', 'azure-keyvault', 'hashicorp-vault'
    vault_secret_path = Column(Text, nullable=True)
    iam_role_arn = Column(Text, nullable=True)  # AWS IAM role ARN or Azure principal ID
    vault_region = Column(String(50), nullable=True)
    
    # For customer-proxy
    proxy_endpoint_url = Column(Text, nullable=True)
    proxy_auth_token_hash = Column(Text, nullable=True)
    
    # For dual-key
    gateway_key_fingerprint = Column(Text, nullable=True)
    emergency_key_fingerprint = Column(Text, nullable=True)
    emergency_key_last_detected = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    last_validated = Column(TIMESTAMP(timezone=True), nullable=True)
    validation_error = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255), nullable=True)
