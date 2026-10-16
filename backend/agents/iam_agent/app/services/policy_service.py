"""IAM Policy Service - Policy management and evaluation."""

import logging
import json
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.policies import (
    PolicyCreate, PolicyUpdate, Policy, PolicyDSL, PolicyRule, Condition, Action,
    EvaluationContext, PolicyEvaluationResult, EvaluationResult,
    PolicyTemplate, PolicyConflict, PolicyAnalysis
)

logger = logging.getLogger(__name__)


class PolicyCloneConflict(Exception):
    """Raised when a clone would violate uniqueness."""

    pass


class PolicyService:
    """Service for policy management and evaluation."""
    
    def __init__(self, db: Session, tenant_id: UUID, realm_name: str):
        """Initialize policy service."""
        self.db = db
        self.tenant_id = tenant_id
        self.realm_name = realm_name
        self.sg_admin_tenant_id = self._get_sg_admin_tenant_id()
    
    # ==================== Policy CRUD ====================
    
    def create_policy(self, policy_data: PolicyCreate, created_by: str) -> Optional[Policy]:
        """Create a new policy."""
        try:
            from sqlalchemy import text
            
            # Validate policy DSL
            if not self._validate_policy_dsl(policy_data.policy_data):
                logger.error("Invalid policy DSL")
                return None
            
            # Ensure JSON serialization for insertion
            policy_json = json.dumps(policy_data.policy_data, default=str)
            
            # Insert policy
            result = self.db.execute(
                text("""
                    INSERT INTO policies (tenant_id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by)
                    VALUES (:tenant_id, :name, :display_name, :description, :policy_type, :scope, :scope_id, :policy_data, :is_active, :priority, :created_by)
                    RETURNING id, created_at, updated_at
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "name": policy_data.name,
                    "display_name": policy_data.display_name,
                    "description": policy_data.description,
                    "policy_type": policy_data.policy_type,
                    "scope": policy_data.scope,
                    "scope_id": str(policy_data.scope_id) if policy_data.scope_id else None,
                    "policy_data": policy_json,
                    "is_active": policy_data.is_active,
                    "priority": policy_data.priority,
                    "created_by": created_by
                }
            )
            row = result.fetchone()
            self.db.commit()

            policy_uuid = row[0] if isinstance(row[0], UUID) else UUID(str(row[0]))
            
            # Extract rules and store them
            self._extract_and_store_rules(policy_uuid, policy_data.policy_data)
            
            return Policy(
                id=policy_uuid,
                tenant_id=self.tenant_id,
                name=policy_data.name,
                display_name=policy_data.display_name,
                description=policy_data.description,
                policy_type=policy_data.policy_type,
                scope=policy_data.scope,
                scope_id=policy_data.scope_id,
                policy_data=policy_data.policy_data,
                is_active=policy_data.is_active,
                priority=policy_data.priority,
                created_by=created_by,
                created_at=row[1],
                updated_at=row[2]
            )
        except Exception as e:
            logger.error(f"Failed to create policy: {e}")
            self.db.rollback()
            return None
    
    def list_policies(self, policy_type: Optional[str] = None, scope: Optional[str] = None, scope_id: Optional[UUID] = None) -> List[Policy]:
        """List policies for tenant."""
        try:
            from sqlalchemy import text
            
            query = """
                SELECT id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by, created_at, updated_at
                FROM policies
                WHERE tenant_id = :tenant_id
            """
            params = {"tenant_id": str(self.tenant_id)}
            
            if policy_type:
                query += " AND policy_type = :policy_type"
                params["policy_type"] = policy_type
            
            if scope:
                query += " AND scope = :scope"
                params["scope"] = scope
            
            if scope_id:
                query += " AND scope_id = :scope_id"
                params["scope_id"] = str(scope_id)
            
            query += " ORDER BY priority ASC, created_at DESC"
            
            result = self.db.execute(text(query), params)
            
            policies = []
            for row in result:
                policies.append(Policy(
                    id=row[0],
                    tenant_id=self.tenant_id,
                    name=row[1],
                    display_name=row[2],
                    description=row[3],
                    policy_type=row[4],
                    scope=row[5],
                    scope_id=UUID(row[6]) if row[6] else None,
                    policy_data=row[7],
                    is_active=row[8],
                    priority=row[9],
                    created_by=row[10],
                    created_at=row[11],
                    updated_at=row[12]
                ))
            return policies
        except Exception as e:
            logger.error(f"Failed to list policies: {e}")
            return []
    
    def get_policy(self, policy_id: UUID) -> Optional[Policy]:
        """Get policy by ID."""
        policies = self.list_policies()
        return next((p for p in policies if p.id == policy_id), None)
    
    def update_policy(self, policy_id: UUID, policy_update: PolicyUpdate) -> bool:
        """Update policy."""
        try:
            from sqlalchemy import text
            
            updates = []
            params = {"policy_id": str(policy_id), "tenant_id": str(self.tenant_id)}
            
            if policy_update.display_name is not None:
                updates.append("display_name = :display_name")
                params["display_name"] = policy_update.display_name
            
            if policy_update.description is not None:
                updates.append("description = :description")
                params["description"] = policy_update.description
            
            if policy_update.policy_data is not None:
                if not self._validate_policy_dsl(policy_update.policy_data):
                    return False
                updates.append("policy_data = :policy_data")
                params["policy_data"] = json.dumps(policy_update.policy_data)
                # Re-extract rules
                self._extract_and_store_rules(policy_id, policy_update.policy_data)
            
            if policy_update.is_active is not None:
                updates.append("is_active = :is_active")
                params["is_active"] = policy_update.is_active
            
            if policy_update.priority is not None:
                updates.append("priority = :priority")
                params["priority"] = policy_update.priority
            
            if not updates:
                return True
            
            updates.append("updated_at = now()")
            
            query = f"""
                UPDATE policies
                SET {', '.join(updates)}
                WHERE id = :policy_id AND tenant_id = :tenant_id
            """
            
            self.db.execute(text(query), params)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update policy: {e}")
            self.db.rollback()
            return False
    
    def delete_policy(self, policy_id: UUID) -> bool:
        """Delete policy."""
        try:
            from sqlalchemy import text
            
            self.db.execute(
                text("DELETE FROM policies WHERE id = :policy_id AND tenant_id = :tenant_id"),
                {"policy_id": str(policy_id), "tenant_id": str(self.tenant_id)}
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete policy: {e}")
            self.db.rollback()
            return False
    
    # ==================== Policy Evaluation ====================
    
    def evaluate_policy(self, policy_type: str, context: EvaluationContext) -> PolicyEvaluationResult:
        """Evaluate policies of a given type against context."""
        try:
            # Get active policies of this type, ordered by priority
            policies = self.list_policies(policy_type=policy_type)
            active_policies = [p for p in policies if p.is_active]
            
            # Evaluate each policy in priority order
            for policy in sorted(active_policies, key=lambda p: p.priority):
                result = self._evaluate_single_policy(policy, context)
                if result:
                    # Log evaluation
                    self._log_evaluation(policy.id, policy_type, context, result)
                    return result
            
            # Default: allow if no policies match
            return PolicyEvaluationResult(
                result="allow",
                policy_id=UUID('00000000-0000-0000-0000-000000000000'),
                matched_rules=[],
                actions=[],
                explanation="No policies matched, defaulting to allow"
            )
        except Exception as e:
            logger.error(f"Failed to evaluate policy: {e}")
            # Fail closed: deny on error
            return PolicyEvaluationResult(
                result="deny",
                policy_id=UUID('00000000-0000-0000-0000-000000000000'),
                matched_rules=[],
                actions=[Action(type="log", value="Policy evaluation error", params={"error": str(e)})],
                explanation="Policy evaluation failed, denying access"
            )
    
    def _evaluate_single_policy(self, policy: Policy, context: EvaluationContext) -> Optional[PolicyEvaluationResult]:
        """Evaluate a single policy."""
        try:
            policy_dsl = PolicyDSL(**policy.policy_data)
            
            # Evaluate rules in order
            matched_rules = []
            actions_to_take = []
            
            for rule in sorted(policy_dsl.rules, key=lambda r: r.priority):
                if self._evaluate_rule(rule, context):
                    matched_rules.append(rule.id)
                    actions_to_take.extend(rule.actions)
                    
                    # Check if we should stop (e.g., deny action)
                    for action in rule.actions:
                        if action.type == "deny":
                            return PolicyEvaluationResult(
                                result="deny",
                                policy_id=policy.id,
                                matched_rules=matched_rules,
                                actions=actions_to_take,
                                explanation=f"Policy '{policy.display_name}' denied access"
                            )
                        elif action.type == "require_approval":
                            return PolicyEvaluationResult(
                                result="require_approval",
                                policy_id=policy.id,
                                matched_rules=matched_rules,
                                actions=actions_to_take,
                                explanation=f"Policy '{policy.display_name}' requires approval"
                            )
                        elif action.type == "require_mfa" or action.type == "require_webauthn":
                            return PolicyEvaluationResult(
                                result="step_up",
                                policy_id=policy.id,
                                matched_rules=matched_rules,
                                actions=actions_to_take,
                                explanation=f"Policy '{policy.display_name}' requires additional authentication"
                            )
            
            # If we have matched rules but no deny/step_up, allow
            if matched_rules:
                return PolicyEvaluationResult(
                    result="allow",
                    policy_id=policy.id,
                    matched_rules=matched_rules,
                    actions=actions_to_take,
                    explanation=f"Policy '{policy.display_name}' allowed access"
                )
            
            return None  # No rules matched
        except Exception as e:
            logger.error(f"Failed to evaluate policy {policy.id}: {e}")
            return None
    
    def _evaluate_rule(self, rule: PolicyRule, context: EvaluationContext) -> bool:
        """Evaluate a rule's conditions against context."""
        if not rule.conditions:
            return True  # No conditions = always match
        
        # All conditions must match (AND logic)
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, context):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: Condition, context: EvaluationContext) -> bool:
        """Evaluate a single condition against context."""
        try:
            # Get value from context based on condition type
            context_value = self._get_context_value(condition.type, context)
            
            if context_value is None:
                return False
            
            # Apply operator
            op = condition.op.lower()
            value = condition.value
            
            if op == "equals":
                return context_value == value
            elif op == "includes" or op == "contains":
                if isinstance(context_value, list):
                    return value in context_value
                elif isinstance(context_value, str):
                    return value in context_value
                return False
            elif op == "in":
                if isinstance(value, list):
                    return context_value in value
                return False
            elif op == "not_in":
                if isinstance(value, list):
                    return context_value not in value
                return False
            elif op == "greater_than":
                return context_value > value
            elif op == "less_than":
                return context_value < value
            elif op == "not_equals":
                return context_value != value
            else:
                logger.warning(f"Unknown operator: {op}")
                return False
        except Exception as e:
            logger.error(f"Failed to evaluate condition: {e}")
            return False
    
    def _get_context_value(self, condition_type: str, context: EvaluationContext) -> Any:
        """Get value from context based on condition type."""
        type_map = {
            "role": context.roles,
            "group": context.groups,
            "department": context.department,
            "ip": context.ip_address,
            "country": context.country,
            "device_known": context.device_known,
            "time_of_day": context.time_of_day,
            "day_of_week": context.day_of_week,
            "risk_level": context.risk_level,
            "risk_score": context.risk_score,
            "user_id": context.user_id,
            "username": context.username,
            "email": context.email,
        }
        return type_map.get(condition_type)
    
    # ==================== Policy Templates ====================
    
    def list_templates(self, policy_type: Optional[str] = None) -> List[PolicyTemplate]:
        """List policy templates (global + tenant-specific)."""
        try:
            from sqlalchemy import text

            # Prefer tenant templates; fall back to sg_admin/global when not overridden
            params = {"tenant_id": str(self.tenant_id)}
            policy_filter = ""
            if policy_type:
                policy_filter = " AND policy_type = :policy_type"
                params["policy_type"] = policy_type

            if self.sg_admin_tenant_id and self.tenant_id != self.sg_admin_tenant_id:
                params["sg_admin_tenant"] = str(self.sg_admin_tenant_id)
                query = f"""
                    SELECT id, name, display_name, description, policy_type, template_data, is_system, category, created_at, updated_at, tenant_id
                    FROM policy_templates pt
                    WHERE pt.tenant_id = :tenant_id {policy_filter}
                    UNION ALL
                    SELECT id, name, display_name, description, policy_type, template_data, is_system, category, created_at, updated_at, tenant_id
                    FROM policy_templates pt
                    WHERE (pt.tenant_id IS NULL OR pt.tenant_id = :sg_admin_tenant) {policy_filter}
                      AND NOT EXISTS (
                        SELECT 1 FROM policy_templates t
                        WHERE t.tenant_id = :tenant_id AND t.name = pt.name
                      )
                    ORDER BY category, display_name
                """
            else:
                query = f"""
                    SELECT id, name, display_name, description, policy_type, template_data, is_system, category, created_at, updated_at, tenant_id
                    FROM policy_templates
                    WHERE (tenant_id IS NULL OR tenant_id = :tenant_id){policy_filter}
                    ORDER BY category, display_name
                """

            result = self.db.execute(text(query), params)
            
            templates = []
            for row in result:
                try:
                    templates.append(PolicyTemplate(
                        id=UUID(row[0]) if isinstance(row[0], str) else row[0],
                        name=row[1],
                        display_name=row[2],
                        description=row[3],
                        policy_type=row[4],
                        template_data=row[5],
                        is_system=row[6],
                        category=row[7],
                        created_at=row[8],
                        updated_at=row[9],
                        tenant_id=row[10] if len(row) > 10 else None
                    ))
                except Exception as row_error:
                    logger.error(f"Failed to parse template row: {row_error}, row data: {row}")
                    continue
            
            logger.info(f"Loaded {len(templates)} policy templates (policy_type={policy_type})")
            return templates
        except Exception as e:
            logger.error(f"Failed to list templates: {e}", exc_info=True)
            return []

    def _get_sg_admin_tenant_id(self) -> Optional[UUID]:
        """Return sg_admin tenant id if present (used for shared templates)."""
        try:
            result = self.db.execute(
                text("SELECT id FROM tenants WHERE slug = 'sg_admin' LIMIT 1")
            ).scalar()
            return UUID(str(result)) if result else None
        except Exception:
            return None
    
    def create_policy_from_template(self, template_id: UUID, name: str, display_name: str, created_by: str) -> Optional[Policy]:
        """Create a policy from a template."""
        try:
            templates = self.list_templates()
            template = next((t for t in templates if t.id == template_id), None)
            if not template:
                return None
            
            policy_data = PolicyCreate(
                name=name,
                display_name=display_name,
                description=template.description,
                policy_type=template.policy_type,
                policy_data=template.template_data,
                is_active=True,
                priority=100
            )
            
            return self.create_policy(policy_data, created_by)
        except Exception as e:
            logger.error(f"Failed to create policy from template: {e}")
            return None
    
    # ==================== Helper Methods ====================
    def list_seed_policies(self) -> List[Policy]:
        """List shared seed policies from sg_admin tenant (if available)."""
        if not self.sg_admin_tenant_id:
            return []
        try:
            result = self.db.execute(
                text("""
                    SELECT id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by, created_at, updated_at
                    FROM policies
                    WHERE tenant_id = :seed_tenant
                    ORDER BY policy_type, priority ASC
                """),
                {"seed_tenant": str(self.sg_admin_tenant_id)}
            )
            seeds: List[Policy] = []
            for row in result:
                seeds.append(Policy(
                    id=UUID(str(row[0])),
                    tenant_id=self.sg_admin_tenant_id,
                    name=row[1],
                    display_name=row[2],
                    description=row[3],
                    policy_type=row[4],
                    scope=row[5],
                    scope_id=UUID(str(row[6])) if row[6] else None,
                    policy_data=row[7],
                    is_active=row[8],
                    priority=row[9],
                    created_by=row[10],
                    created_at=row[11],
                    updated_at=row[12]
                ))
            return seeds
        except Exception as e:
            logger.error(f"Failed to list seed policies: {e}", exc_info=True)
            return []

    def _row_to_policy(self, row) -> Policy:
        """Convert a raw DB row to a Policy model."""
        return Policy(
            id=UUID(str(row[0])),
            tenant_id=self.tenant_id,
            name=row[1],
            display_name=row[2],
            description=row[3],
            policy_type=row[4],
            scope=row[5],
            scope_id=UUID(str(row[6])) if row[6] else None,
            policy_data=row[7],
            is_active=row[8],
            priority=row[9],
            created_by=row[10],
            created_at=row[11],
            updated_at=row[12],
        )

    def _normalize_seed_policy_data(
        self, seed_policy_id: UUID, seed_policy_data: Dict[str, Any], policy_type: str, scope: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Normalize seed policy JSON into a valid PolicyDSL shape."""
        try:
            if not isinstance(seed_policy_data, dict):
                return None

            normalized = json.loads(json.dumps(seed_policy_data))  # deep copy
            normalized.setdefault("id", f"seed-{seed_policy_id}")
            normalized.setdefault("type", policy_type or "authorization")
            normalized.setdefault("scope", scope or "tenant")
            normalized.setdefault("rules", seed_policy_data.get("rules", []))

            rules = []
            for idx, rule in enumerate(normalized.get("rules", [])):
                if not isinstance(rule, dict):
                    continue
                rule_id = rule.get("id") or f"rule-{idx+1}"
                conditions = []
                for cond in rule.get("conditions", []):
                    if not isinstance(cond, dict):
                        continue
                    conditions.append(
                        {
                            "type": cond.get("type") or cond.get("attribute") or "attribute",
                            "op": cond.get("op") or cond.get("operator") or "equals",
                            "value": cond.get("value"),
                            "field": cond.get("field"),
                        }
                    )
                actions = []
                for act in rule.get("actions", []):
                    if isinstance(act, dict):
                        actions.append(
                            {
                                "type": act.get("type") or act.get("action") or act.get("effect") or "allow",
                                "value": act.get("value"),
                                "params": act.get("params"),
                            }
                        )
                    else:
                        actions.append({"type": str(act) or "allow", "value": None})
                if not conditions:
                    conditions = [{"type": "always", "op": "equals", "value": True}]
                if not actions:
                    actions = [{"type": "allow"}]
                rules.append(
                    {
                        "id": rule_id,
                        "name": rule.get("name") or f"Rule {idx+1}",
                        "description": rule.get("description"),
                        "conditions": conditions,
                        "actions": actions,
                        "priority": rule.get("priority", 100),
                    }
                )

            normalized["rules"] = rules
            return normalized
        except Exception as exc:
            logger.error(f"Failed to normalize seed policy {seed_policy_id}: {exc}", exc_info=True)
            return None

    def clone_seed_policy(
        self,
        seed_policy_id: UUID,
        created_by: str,
        name_override: Optional[str] = None,
        display_name_override: Optional[str] = None,
    ) -> Optional[Policy]:
        """Clone a seed policy from sg_admin into the current tenant."""
        if not self.sg_admin_tenant_id:
            logger.warning("sg_admin tenant not found; cannot clone seed policies")
            return None
        try:
            seed = self.db.execute(
                text("""
                    SELECT id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by, created_at, updated_at
                    FROM policies
                    WHERE tenant_id = :seed_tenant AND id = :pid
                    LIMIT 1
                """),
                {"seed_tenant": str(self.sg_admin_tenant_id), "pid": str(seed_policy_id)}
            ).fetchone()
            if not seed:
                return None
            target_name = name_override or f"{seed[1]}-{self.tenant_id}"
            target_display_name = display_name_override or seed[2] or seed[1]

            # If a policy with the same name already exists, treat it as idempotent unless the user asked for a custom name.
            existing = self.db.execute(
                text(
                    """
                    SELECT id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by, created_at, updated_at
                    FROM policies
                    WHERE tenant_id = :tenant_id AND name = :name
                    LIMIT 1
                    """
                ),
                {"tenant_id": str(self.tenant_id), "name": target_name},
            ).fetchone()
            if existing:
                if name_override:
                    raise PolicyCloneConflict("A policy with this name already exists.")
                return self._row_to_policy(existing)

            normalized_dsl = self._normalize_seed_policy_data(seed_policy_id, seed[7], seed[4], seed[5])
            if not normalized_dsl:
                logger.error(f"Seed policy {seed_policy_id} could not be normalized; skipping clone")
                return None

            policy_data = PolicyCreate(
                name=target_name,
                display_name=target_display_name,
                description=seed[3],
                policy_type=seed[4],
                scope=seed[5],
                scope_id=UUID(str(seed[6])) if seed[6] else None,
                policy_data=normalized_dsl,
                is_active=seed[8],
                priority=seed[9]
            )
            return self.create_policy(policy_data, created_by)
        except PolicyCloneConflict:
            raise
        except Exception as e:
            logger.error(f"Failed to clone seed policy {seed_policy_id}: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def _validate_policy_dsl(self, policy_data: Dict[str, Any]) -> bool:
        """Validate policy DSL structure."""
        try:
            # Basic validation
            if not isinstance(policy_data, dict):
                return False
            
            if "id" not in policy_data or "type" not in policy_data or "rules" not in policy_data:
                return False
            
            if not isinstance(policy_data["rules"], list):
                return False
            
            # Validate rules
            for rule in policy_data["rules"]:
                if not isinstance(rule, dict):
                    return False
                if "id" not in rule or "conditions" not in rule or "actions" not in rule:
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Policy DSL validation error: {e}")
            return False
    
    def _extract_and_store_rules(self, policy_id: UUID, policy_data: Dict[str, Any]):
        """Extract rules from policy DSL and store them."""
        try:
            from sqlalchemy import text
            
            # Delete existing rules
            self.db.execute(
                text("DELETE FROM policy_rules WHERE policy_id = :policy_id"),
                {"policy_id": str(policy_id)}
            )
            
            # Insert new rules
            policy_dsl = PolicyDSL(**policy_data)
            for rule in policy_dsl.rules:
                self.db.execute(
                    text("""
                        INSERT INTO policy_rules (policy_id, rule_id, name, description, conditions, actions, priority, is_active)
                        VALUES (:policy_id, :rule_id, :name, :description, :conditions, :actions, :priority, :is_active)
                    """),
                    {
                        "policy_id": str(policy_id),
                        "rule_id": rule.id,
                        "name": rule.name,
                        "description": rule.description,
                        "conditions": [c.dict() for c in rule.conditions],
                        "actions": [a.dict() for a in rule.actions],
                        "priority": rule.priority,
                        "is_active": True
                    }
                )
            
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to extract and store rules: {e}")
            self.db.rollback()
    
    def _log_evaluation(self, policy_id: UUID, evaluation_type: str, context: EvaluationContext, result: PolicyEvaluationResult):
        """Log policy evaluation."""
        try:
            from sqlalchemy import text
            
            self.db.execute(
                text("""
                    INSERT INTO policy_evaluations (tenant_id, policy_id, evaluation_type, context, result, matched_rules, actions_taken)
                    VALUES (:tenant_id, :policy_id, :evaluation_type, :context, :result, :matched_rules, :actions_taken)
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "policy_id": str(policy_id),
                    "evaluation_type": evaluation_type,
                    "context": context.dict(),
                    "result": result.result,
                    "matched_rules": result.matched_rules,
                    "actions_taken": [a.dict() for a in result.actions]
                }
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log evaluation: {e}")
