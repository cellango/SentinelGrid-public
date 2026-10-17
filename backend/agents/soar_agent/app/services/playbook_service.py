"""Playbook service for CRUD operations."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, update, delete, exists, and_, or_, text
from sqlalchemy.orm import Session, aliased

from app.models import (
    Playbook,
    PlaybookCreate,
    PlaybookUpdate,
    PlaybookCopy,
    PlaybookValidationResult,
)

def _slugify(value: str) -> str:
    """Generate a simple, URL-safe-ish key from a name."""
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value or "")
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned or f"playbook-{uuid4().hex[:6]}"


class PlaybookService:
    """Service for playbook management."""

    def __init__(self, db: Session):
        self.db = db
        self.sg_admin_tenant_id = self._get_sg_admin_tenant_id()

    def create(self, tenant_id: UUID, playbook_data: PlaybookCreate, created_by: Optional[UUID] = None) -> Playbook:
        """Create a new playbook."""
        from app.database import PlaybookDB  # Avoid circular import

        key_value = playbook_data.key or playbook_data.playbook_key or _slugify(playbook_data.name)
        playbook_key_value = playbook_data.playbook_key or key_value

        playbook = PlaybookDB(
            id=uuid4(),
            tenant_id=tenant_id,
            key=key_value,
            name=playbook_data.name,
            description=playbook_data.description,
            category=playbook_data.category,
            version=playbook_data.version,
            playbook_key=playbook_key_value,
            is_builtin=playbook_data.is_builtin,
            severity_default=playbook_data.severity_default,
            applicable_sources=playbook_data.applicable_sources,
            triggers=playbook_data.triggers,
            prerequisites=playbook_data.prerequisites,
            artifacts_required=playbook_data.artifacts_required,
            phases=playbook_data.phases,
            cis_controls=playbook_data.cis_controls,
            workflow=playbook_data.workflow.model_dump(),
            timeout_seconds=playbook_data.timeout_seconds,
            retry_policy=playbook_data.retry_policy.model_dump() if playbook_data.retry_policy else None,
            on_failure=playbook_data.on_failure,
            is_template=playbook_data.is_template,
            requires_approval=playbook_data.requires_approval,
            tags=playbook_data.tags,
            nist_controls=playbook_data.nist_controls,
            mitre_tactics=playbook_data.mitre_tactics,
            mitre_techniques=playbook_data.mitre_techniques,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            trigger_conditions=playbook_data.trigger_conditions,
            auto_trigger_enabled=playbook_data.auto_trigger_enabled,
            trigger_priority=playbook_data.trigger_priority,
        )

        self.db.add(playbook)
        self.db.commit()
        self.db.refresh(playbook)

        return self._to_model(playbook)

    def get_by_id(self, playbook_id: UUID, tenant_id: UUID) -> Optional[Playbook]:
        """Get playbook by ID."""
        from app.database import PlaybookDB

        if self.sg_admin_tenant_id and tenant_id != self.sg_admin_tenant_id:
            stmt = select(PlaybookDB).where(
                PlaybookDB.id == playbook_id,
                or_(
                    PlaybookDB.tenant_id == tenant_id,
                    and_(
                        PlaybookDB.tenant_id == self.sg_admin_tenant_id,
                        PlaybookDB.is_builtin.is_(True),
                    ),
                ),
            )
        else:
            stmt = select(PlaybookDB).where(
                PlaybookDB.id == playbook_id,
                (PlaybookDB.tenant_id == tenant_id) | (PlaybookDB.is_builtin.is_(True))
            )
        result = self.db.execute(stmt).scalar_one_or_none()
        return self._to_model(result) if result else None

    def list(
        self,
        tenant_id: UUID,
        category: Optional[str] = None,
        is_template: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Playbook]:
        """List playbooks for tenant."""
        from app.database import PlaybookDB

        # Tenant-owned playbooks
        tenant_stmt = select(PlaybookDB).where(PlaybookDB.tenant_id == tenant_id)
        if category:
            tenant_stmt = tenant_stmt.where(PlaybookDB.category == category)
        if is_template is not None:
            tenant_stmt = tenant_stmt.where(PlaybookDB.is_template == is_template)
        tenant_results = self.db.execute(tenant_stmt).scalars().all()

        # Shared (sg_admin) playbooks not overridden by tenant
        shared_results = []
        if self.sg_admin_tenant_id and tenant_id != self.sg_admin_tenant_id:
            pb_alias = aliased(PlaybookDB)
            shared_stmt = select(PlaybookDB).where(
                PlaybookDB.tenant_id == self.sg_admin_tenant_id,
                PlaybookDB.is_builtin.is_(True),
                ~exists().where(
                    and_(
                        pb_alias.tenant_id == tenant_id,
                        or_(
                            pb_alias.key == PlaybookDB.key,
                            and_(
                                pb_alias.playbook_key.isnot(None),
                                pb_alias.playbook_key == PlaybookDB.playbook_key,
                            ),
                        ),
                    )
                ),
            )
            if category:
                shared_stmt = shared_stmt.where(PlaybookDB.category == category)
            if is_template is not None:
                shared_stmt = shared_stmt.where(PlaybookDB.is_template == is_template)
            shared_results = self.db.execute(shared_stmt).scalars().all()

        combined = tenant_results + shared_results
        combined.sort(key=lambda pb: (pb.updated_at or pb.created_at), reverse=True)

        if skip:
            combined = combined[skip:]
        if limit is not None:
            combined = combined[:limit]

        return [self._to_model(result) for result in combined]

    def update(
        self,
        playbook_id: UUID,
        tenant_id: UUID,
        playbook_data: PlaybookUpdate
    ) -> Optional[Playbook]:
        """Update playbook."""
        from app.database import PlaybookDB

        update_data = playbook_data.model_dump(exclude_unset=True)
        if not update_data:
            return self.get_by_id(playbook_id, tenant_id)

        update_data["updated_at"] = datetime.utcnow()
        if "workflow" in update_data and update_data["workflow"]:
            if hasattr(update_data["workflow"], "model_dump"):
                update_data["workflow"] = update_data["workflow"].model_dump()
            elif isinstance(update_data["workflow"], dict):
                # Already a dict, keep as is
                pass
        if "retry_policy" in update_data and update_data["retry_policy"]:
            if hasattr(update_data["retry_policy"], "model_dump"):
                update_data["retry_policy"] = update_data["retry_policy"].model_dump()
            elif isinstance(update_data["retry_policy"], dict):
                # Already a dict, keep as is
                pass
        # trigger_conditions may be dict already

        stmt = (
            update(PlaybookDB)
            .where(
                PlaybookDB.id == playbook_id,
                PlaybookDB.tenant_id == tenant_id
            )
            .values(**update_data)
            .returning(PlaybookDB)
        )

        result = self.db.execute(stmt).scalar_one_or_none()
        self.db.commit()

        return self._to_model(result) if result else None

    def delete(self, playbook_id: UUID, tenant_id: UUID) -> bool:
        """Delete playbook."""
        from app.database import PlaybookDB

        stmt = delete(PlaybookDB).where(
            PlaybookDB.id == playbook_id,
            PlaybookDB.tenant_id == tenant_id
        )
        result = self.db.execute(stmt)
        self.db.commit()

        return result.rowcount > 0

    def set_approval_status(self, playbook_id: UUID, tenant_id: UUID, approve: bool) -> Optional[Playbook]:
        """Approve or reject a playbook by toggling is_enabled."""
        from app.database import PlaybookDB

        stmt = (
            update(PlaybookDB)
            .where(PlaybookDB.id == playbook_id, PlaybookDB.tenant_id == tenant_id)
            .values(
                is_enabled=approve,
                updated_at=datetime.utcnow()
            )
            .returning(PlaybookDB)
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        self.db.commit()
        return self._to_model(result) if result else None

    def copy(
        self,
        playbook_id: UUID,
        tenant_id: UUID,
        copy_request: PlaybookCopy
    ) -> Optional[Playbook]:
        """Copy/duplicate a playbook."""
        original = self.get_by_id(playbook_id, tenant_id)
        if not original:
            return None

        base_key = original.key or original.playbook_key or _slugify(original.name)
        new_key = copy_request.new_key or f"{base_key}-copy"

        # Create new playbook from original
        new_playbook_data = PlaybookCreate(
            name=copy_request.new_name,
            key=new_key,
            description=original.description,
            category=original.category,
            playbook_key=original.playbook_key or base_key,
            is_builtin=False,
            severity_default=original.severity_default,
            applicable_sources=original.applicable_sources,
            triggers=original.triggers,
            prerequisites=original.prerequisites,
            artifacts_required=original.artifacts_required,
            phases=original.phases,
            cis_controls=original.cis_controls,
            version=copy_request.new_version or original.version or "1.0.0",
            workflow=original.workflow,
            timeout_seconds=original.timeout_seconds,
            retry_policy=original.retry_policy,
            on_failure=original.on_failure,
            is_template=False,  # Copy is not a template
            requires_approval=True,  # Custom/clone should go through approval
            tags=original.tags.copy(),
            nist_controls=original.nist_controls.copy() if original.nist_controls else [],
            mitre_tactics=original.mitre_tactics.copy() if original.mitre_tactics else [],
            mitre_techniques=original.mitre_techniques.copy() if original.mitre_techniques else [],
            trigger_conditions=original.trigger_conditions,
            auto_trigger_enabled=original.auto_trigger_enabled or False,
            trigger_priority=original.trigger_priority or 0,
        )

        return self.create(tenant_id, new_playbook_data, original.created_by)

    def validate(self, playbook: Playbook) -> PlaybookValidationResult:
        """Validate playbook structure."""
        errors = []
        warnings = []

        # Check for at least one trigger node
        trigger_nodes = [
            node for node in playbook.workflow.nodes
            if node.get("type") in ["alert_trigger", "incident_trigger", "manual_trigger", "scheduled_trigger"]
        ]
        if not trigger_nodes:
            errors.append("Playbook must have at least one trigger node")

        # Check for valid node connections
        node_ids = {node["id"] for node in playbook.workflow.nodes}
        for edge in playbook.workflow.edges:
            if edge.get("source") not in node_ids:
                errors.append(f"Edge references non-existent source node: {edge.get('source')}")
            if edge.get("target") not in node_ids:
                errors.append(f"Edge references non-existent target node: {edge.get('target')}")

        # Check for terminal nodes
        terminal_nodes = [
            node for node in playbook.workflow.nodes
            if node.get("type") in ["success", "failure", "escalation"]
        ]
        if not terminal_nodes:
            warnings.append("Playbook has no terminal nodes (success/failure/escalation)")

        # Validate timeout
        if playbook.timeout_seconds < 0:
            errors.append("timeout_seconds must be non-negative")
        if playbook.timeout_seconds > 86400:  # 24 hours
            warnings.append("Playbook timeout is very long (>24 hours)")

        return PlaybookValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def _to_model(db_playbook) -> Playbook:
        """Convert database model to Pydantic model."""
        from app.models import WorkflowStructure, RetryPolicy

        return Playbook(
            id=db_playbook.id,
            tenant_id=db_playbook.tenant_id,
            key=getattr(db_playbook, "key", None),
            playbook_key=getattr(db_playbook, "playbook_key", None),
            name=db_playbook.name,
            description=db_playbook.description,
            category=db_playbook.category,
            version=db_playbook.version,
            workflow=WorkflowStructure(**db_playbook.workflow) if isinstance(db_playbook.workflow, dict) else db_playbook.workflow,
            timeout_seconds=db_playbook.timeout_seconds,
            retry_policy=RetryPolicy(**db_playbook.retry_policy) if db_playbook.retry_policy else None,
            on_failure=db_playbook.on_failure,
            is_template=db_playbook.is_template,
            requires_approval=db_playbook.requires_approval,
            tags=db_playbook.tags or [],
            is_builtin=getattr(db_playbook, "is_builtin", False),
            severity_default=getattr(db_playbook, "severity_default", None),
            applicable_sources=getattr(db_playbook, "applicable_sources", []) or [],
            triggers=getattr(db_playbook, "triggers", []) or [],
            prerequisites=getattr(db_playbook, "prerequisites", []) or [],
            artifacts_required=getattr(db_playbook, "artifacts_required", []) or [],
            phases=getattr(db_playbook, "phases", None),
            cis_controls=getattr(db_playbook, "cis_controls", []) or [],
            nist_controls=db_playbook.nist_controls or [],
            mitre_tactics=db_playbook.mitre_tactics or [],
            mitre_techniques=db_playbook.mitre_techniques or [],
            trigger_conditions=db_playbook.trigger_conditions,
            auto_trigger_enabled=db_playbook.auto_trigger_enabled,
            trigger_priority=db_playbook.trigger_priority or 0,
            created_by=db_playbook.created_by,
            created_at=db_playbook.created_at,
            updated_at=db_playbook.updated_at,
            n8n_workflow_id=db_playbook.n8n_workflow_id,
            n8n_webhook_url=db_playbook.n8n_webhook_url,
        )

    def _get_sg_admin_tenant_id(self) -> Optional[UUID]:
        """Fetch sg_admin tenant id for shared/built-in resources."""
        try:
            result = self.db.execute(
                text("SELECT id FROM tenants WHERE slug = 'sg_admin' LIMIT 1")
            ).scalar()
            return UUID(str(result)) if result else None
        except Exception:
            return None
