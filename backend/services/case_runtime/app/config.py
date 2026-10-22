"""Owned configuration; no existing DB is opened by default."""

from urllib.parse import urlsplit, parse_qs
from pydantic import Field, model_validator
from sg_core.http_rate_limit import RateLimitPolicy
from pydantic_settings import BaseSettings, SettingsConfigDict
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding, UserPrincipalSettings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )
    ENVIRONMENT: str = "development"
    IAM_AGENT_URL: str = "http://iam_agent:8000"
    KEYCLOAK_CLIENT_ID: str = "sentinelgrid-web"
    IAM_TOKEN_VALIDATION_TIMEOUT: float = Field(
        default=5, gt=0, le=10, allow_inf_nan=False
    )
    IAM_VERIFIER_CA_BUNDLE: str | None = None
    IAM_USER_CLIENT_BINDINGS: tuple[UserClientBinding, ...] = ()
    ACTION_RATE_POLICY: RateLimitPolicy = Field(default_factory=RateLimitPolicy)
    ACTION_AUTHORITY_ENABLED: bool = False
    ACTION_AUTHORITY_DATABASE_URL: str | None = None
    ACTION_POLICY_VERSION: str = "action-policy-v1"

    @model_validator(mode="after")
    def owned_config(self):
        self.verification_settings()
        self.user_settings()
        policy = self.ACTION_RATE_POLICY
        if self.ENVIRONMENT not in {"development", "test"} and (
            not policy.enabled
            or not policy.fail_closed
            or not policy.redis_url.startswith("rediss://")
        ):
            raise ValueError(
                "Non-development action authority requires TLS Redis and fail-closed budgets"
            )
        if self.ACTION_AUTHORITY_ENABLED:
            p = urlsplit(self.ACTION_AUTHORITY_DATABASE_URL or "")
            if (
                p.scheme != "postgresql+psycopg2"
                or not p.path
                or p.fragment
                or any(
                    len(v) != 1
                    for v in parse_qs(p.query, keep_blank_values=True).values()
                )
            ):
                raise ValueError("Owned PostgreSQL URL required")
            if self.ENVIRONMENT not in {"development", "test"} and parse_qs(
                p.query
            ).get("sslmode") != ["verify-full"]:
                raise ValueError("Authority database TLS verify-full required")
        if self.ACTION_POLICY_VERSION != "action-policy-v1":
            raise ValueError("Unsupported action policy version")
        return self

    def verification_settings(self):
        return IAMVerificationSettings(
            _env_file=None,
            **self.model_dump(
                include={
                    "ENVIRONMENT",
                    "IAM_AGENT_URL",
                    "KEYCLOAK_CLIENT_ID",
                    "IAM_TOKEN_VALIDATION_TIMEOUT",
                    "IAM_VERIFIER_CA_BUNDLE",
                }
            ),
        )

    def user_settings(self):
        return UserPrincipalSettings(
            _env_file=None,
            ENVIRONMENT=self.ENVIRONMENT,
            IAM_USER_CLIENT_BINDINGS=self.IAM_USER_CLIENT_BINDINGS,
        )
