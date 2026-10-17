"""Transactional local service-account credentials, disabled until explicitly enabled.

No provider clients, token exchange, API permissions or entitlement writers exist
here. Credential checks are administrator-side local proofs, not API authentication.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID, uuid4
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.api.request_context import ensure_request_has_any_role
from app.core.config import settings
from app.models.service_account import ServiceAccount
from app.schemas.nhi import (
    CreateServiceAccountRequest,
    LifecycleRequest,
    ServiceAccountResponse,
    IssuedCredentialResponse,
)
from app.services.audit_logger import AuditLogger


def require_nhi_admin(context):
    try:
        if not isinstance(context.tenant_id, UUID):
            raise ValueError("Tenant context must be a UUID")
        actor = UUID(str(context.user_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401, detail="Verified tenant and user UUIDs are required"
        )
    ensure_request_has_any_role(context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN")
    if not settings.IAM_ENABLE_SERVICE_ACCOUNTS:
        raise HTTPException(
            status_code=501, detail="Local service account governance is not enabled"
        )
    return actor


def unavailable_api_keys():
    raise HTTPException(
        status_code=503,
        detail="API key persistence, scope enforcement and authentication are not qualified",
    )


class NHIService:
    def __init__(self, db, context):
        self.db = db
        self.context = context

    def _query(self):
        return self.db.query(ServiceAccount).filter(
            ServiceAccount.tenant_id == self.context.tenant_id
        )

    def _change(self, write):
        try:
            result = write()
            self.db.commit()
            return result
        except Exception as error:
            try:
                self.db.rollback()
            except Exception:
                pass
            if isinstance(error, HTTPException):
                raise
            if (
                isinstance(error, IntegrityError)
                and getattr(getattr(error.orig, "diag", None), "constraint_name", None)
                == "iam_service_account_name"
            ):
                raise HTTPException(
                    status_code=409, detail="Service account name already exists"
                ) from error
            raise HTTPException(
                status_code=503,
                detail="Local identity change could not be confirmed; inspect current version before retry",
            ) from error

    def _response(self, row):
        return ServiceAccountResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            client_id=row.client_id,
            owner_user_id=row.owner_user_id,
            created_by=row.created_by,
            status=row.status,
            rotation_days=row.rotation_days,
            credential_version=row.credential_version,
            credential_expires_at=row.credential_expires_at,
            credential_expired=row.credential_expires_at is not None
            and row.credential_expires_at <= datetime.now(timezone.utc),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _snapshot(self, row):
        # No digest, plaintext, free-text definition or caller metadata in audit.
        return dict(
            id=str(row.id),
            owner_user_id=str(row.owner_user_id),
            status=row.status,
            credential_version=row.credential_version,
            rotation_days=row.rotation_days,
            credential_expires_at=row.credential_expires_at,
        )

    def _audit(self, row, actor, action, before=None, reason=None):
        AuditLogger(self.db).log_entitlement_event(
            "nhi_" + action,
            None,
            self.context.tenant_id,
            actor,
            subject_id=row.id,
            reason=reason,
            changes={
                "before": before,
                "after": self._snapshot(row),
                "credential_scope": "local_registry_only",
                "provider_effects": [],
            },
        )

    def _issue(self, row):
        secret = secrets.token_urlsafe(48)
        row.secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        row.credential_expires_at = datetime.now(timezone.utc) + timedelta(
            days=row.rotation_days
        )
        return secret

    def create_service_account(self, request):
        actor = require_nhi_admin(self.context)
        request = CreateServiceAccountRequest.model_validate(request)

        def create():
            identity = uuid4()
            row = ServiceAccount(
                id=identity,
                tenant_id=self.context.tenant_id,
                name=request.name,
                description=request.description,
                client_id="sa-" + str(identity),
                owner_user_id=actor,
                created_by=actor,
                status="active",
                rotation_days=request.rotation_days,
                credential_version=1,
            )
            secret = self._issue(row)
            self.db.add(row)
            self.db.flush()
            self._audit(row, actor, "created")
            return IssuedCredentialResponse(
                **self._response(row).model_dump(), client_secret=secret
            )

        return self._change(create)

    def get_service_account(self, account_id):
        require_nhi_admin(self.context)
        try:
            row = (
                self._query().filter(ServiceAccount.id == UUID(str(account_id))).first()
            )
            if row is None:
                raise HTTPException(status_code=404, detail="Service account not found")
            return self._response(row)
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(
                status_code=503, detail="Local identity registry unavailable"
            ) from error

    def list_service_accounts(self, status=None, within_days=None):
        require_nhi_admin(self.context)
        if status is not None and status not in {"active", "inactive", "deleted"}:
            raise HTTPException(status_code=400, detail="Invalid account status")
        if within_days is not None and (
            type(within_days) is not int or not 0 <= within_days <= 365
        ):
            raise HTTPException(status_code=400, detail="Invalid expiry window")
        try:
            query = self._query()
            if status is not None:
                query = query.filter(ServiceAccount.status == status)
            if within_days is not None:
                query = query.filter(
                    ServiceAccount.status == "active",
                    ServiceAccount.credential_expires_at
                    <= datetime.now(timezone.utc) + timedelta(days=within_days),
                )
            rows = (
                query.order_by(ServiceAccount.created_at, ServiceAccount.id)
                .limit(101)
                .all()
            )
            if len(rows) > 100:
                raise HTTPException(
                    status_code=409,
                    detail="Local identity inventory exceeds bounded list",
                )
            return [self._response(row) for row in rows]
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(
                status_code=503, detail="Local identity registry unavailable"
            ) from error

    def transition(self, account_id, operation, request):
        actor = require_nhi_admin(self.context)
        request = LifecycleRequest.model_validate(request)
        if operation not in {"rotate", "deactivate", "activate", "delete"}:
            raise HTTPException(
                status_code=400, detail="Unsupported local identity operation"
            )
        account_id = UUID(str(account_id))

        def change():
            row = (
                self._query()
                .filter(ServiceAccount.id == account_id)
                .populate_existing()
                .with_for_update()
                .first()
            )
            if row is None:
                raise HTTPException(status_code=404, detail="Service account not found")
            if row.credential_version != request.expected_version:
                raise HTTPException(
                    status_code=409,
                    detail="Credential version changed; inspect current state",
                )
            allowed = {
                "rotate": {"active"},
                "deactivate": {"active"},
                "activate": {"inactive"},
                "delete": {"active", "inactive"},
            }
            if row.status not in allowed[operation]:
                raise HTTPException(
                    status_code=409, detail="Invalid local identity transition"
                )
            before = self._snapshot(row)
            row.credential_version += 1
            secret = None
            if operation in {"rotate", "activate"}:
                row.status = "active"
                secret = self._issue(row)
            else:
                row.status = "inactive" if operation == "deactivate" else "deleted"
                row.secret_hash = None
                row.credential_expires_at = None
            self.db.flush()
            self._audit(row, actor, operation, before, request.reason)
            response = self._response(row)
            return (
                IssuedCredentialResponse(**response.model_dump(), client_secret=secret)
                if secret is not None
                else response
            )

        return self._change(change)

    def check_credentials(self, client_id, client_secret):
        """Admin-side local proof only; no JWT, scopes, roles or permission result."""
        actor = require_nhi_admin(self.context)
        if (
            not isinstance(client_id, str)
            or len(client_id) > 40
            or not isinstance(client_secret, str)
            or not 1 <= len(client_secret) <= 128
        ):
            raise HTTPException(
                status_code=400, detail="Invalid credential proof input"
            )

        def check():
            row = (
                self._query()
                .filter(ServiceAccount.client_id == client_id)
                .populate_existing()
                .with_for_update(read=True)
                .first()
            )
            digest = hashlib.sha256(client_secret.encode()).hexdigest()
            matched = secrets.compare_digest(
                digest,
                row.secret_hash if row is not None and row.secret_hash else "0" * 64,
            )
            valid = bool(
                matched
                and row is not None
                and row.status == "active"
                and row.credential_expires_at > datetime.now(timezone.utc)
            )
            AuditLogger(self.db).log_entitlement_event(
                "nhi_credential_checked",
                None,
                self.context.tenant_id,
                actor,
                subject_id=row.id if row else None,
                decision="allow" if valid else "deny",
                reason="Administrator-side local credential proof only",
                changes={
                    "credential_scope": "local_registry_only",
                    "credential_version": row.credential_version if row else None,
                    "provider_effects": [],
                },
            )
            return valid

        return self._change(check)
