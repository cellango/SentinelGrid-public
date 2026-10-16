"""Configuration settings for Model Gateway service."""

import os
from typing import Optional

from pydantic import model_validator
from pydantic_settings import SettingsConfigDict

from sg_core.service_security import (
    ServiceSecuritySettings,
    require_authenticated_redis_url,
    require_non_default_database_url,
)


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_CORS_ALLOWLIST_IN_PROD = False
    REQUIRE_INTERNAL_TOKEN_IN_PROD = True

    # Service info
    SERVICE_NAME: str = "model-gateway"
    VERSION: str = "0.2.0"

    # Base model configuration
    BASE_MODEL_NAME: str = os.getenv("BASE_MODEL_NAME", "cybergpt-7b")
    BASE_MODEL_PATH: str = os.getenv("BASE_MODEL_PATH", "/models/base")
    BASE_MODEL_HUGGINGFACE_ID: Optional[str] = os.getenv(
        "BASE_MODEL_HUGGINGFACE_ID",
        "microsoft/phi-2",
    )

    # LLM runtime configuration
    LLM_RUNTIME: str = os.getenv("LLM_RUNTIME", "transformers")
    LLM_N_THREADS: int = int(os.getenv("LLM_N_THREADS", "4"))
    LLM_N_CTX: int = int(os.getenv("LLM_N_CTX", "4096"))

    # GPU configuration
    CUDA_VISIBLE_DEVICES: Optional[str] = os.getenv("CUDA_VISIBLE_DEVICES")

    # vLLM configuration
    VLLM_TENSOR_PARALLEL_SIZE: int = int(os.getenv("VLLM_TENSOR_PARALLEL_SIZE", "1"))

    # Adapter configuration
    ADAPTER_STORAGE_PATH: str = os.getenv("ADAPTER_STORAGE_PATH", "/models/adapters")
    ADAPTER_CACHE_SIZE: int = int(os.getenv("ADAPTER_CACHE_SIZE", "10"))

    # Database configuration
    MODEL_GATEWAY_DATABASE_URL: str = os.getenv(
        "MODEL_GATEWAY_DATABASE_URL",
        os.getenv("DATABASE_URL", "postgresql://sg:sg@localhost:5432/sg"),
    )

    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Embeddings configuration
    EMBEDDINGS_MODEL: str = os.getenv("EMBEDDINGS_MODEL", "BAAI/bge-m3")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    # Model gateway URL (for other services)
    MODEL_GATEWAY_URL: str = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @model_validator(mode="after")
    def _validate_security_posture(self):
        super()._validate_security_posture()
        require_non_default_database_url(
            self.ENVIRONMENT,
            self.MODEL_GATEWAY_DATABASE_URL,
            "MODEL_GATEWAY_DATABASE_URL",
        )
        require_authenticated_redis_url(self.ENVIRONMENT, self.REDIS_URL, "REDIS_URL")
        return self


settings = Settings()
