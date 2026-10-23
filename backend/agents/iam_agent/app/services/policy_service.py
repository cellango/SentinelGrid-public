"""IAM Policy Service - Policy management and evaluation."""

from fastapi import HTTPException
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
    
    def __init__(self, db: Session, tenant_id: UUID, realm_name: str, *, load_seed_tenant: bool = True):
        """Initialize policy service."""
        self.db = db
        self.tenant_id = tenant_id
        self.realm_name = realm_name
        self.sg_admin_tenant_id = self._get_sg_admin_tenant_id() if load_seed_tenant else None
    
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
            policy_uuid = row[0] if isinstance(row[0], UUID) else UUID(str(row[0]))
            
            # Extract rules and store them
            self._extract_and_store_rules(policy_uuid, policy_data.policy_data)
            
            policy = Policy(
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
            self.db.commit()
            return policy
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
                    scope_id=UUID(str(row[6])) if row[6] else None,
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
            
            params = {"policy_id": str(policy_id), "tenant_id": str(self.tenant_id)}
            # Serialize parent and rule replacement, including concurrent updates.
            parent = self.db.execute(text(
                "SELECT id FROM policies WHERE id=:policy_id AND tenant_id=:tenant_id FOR UPDATE"
            ), params).first()
            if parent is None:
                return False
            updates = []
            
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
    
    # There is deliberately no caller-selectable affirmative/first-allow mode.
    _POLICY_TYPES = {"signon", "access", "approval", "sod", "authorization"}
    _ACTIONS = {"allow", "deny", "require_mfa", "require_webauthn", "require_approval", "log", "notify"}
    _OPERATORS = {"equals", "not_equals", "includes", "contains", "in", "not_in", "greater_than", "less_than"}
    _CONTEXT_FIELDS = {
        "role": "roles", "group": "groups", "department": "department",
        "ip": "ip_address", "country": "country", "device_known": "device_known",
        "time_of_day": "time_of_day", "day_of_week": "day_of_week",
        "risk_level": "risk_level", "risk_score": "risk_score",
        "user_id": "user_id", "username": "username", "email": "email",
        "resource": "resource", "resource_type": "resource_type", "action": "action",
    }

    @staticmethod
    def _denied(explanation: str) -> PolicyEvaluationResult:
        return PolicyEvaluationResult(result="deny", policy_id=UUID(int=0),
                                      matched_rules=[], actions=[], explanation=explanation)

    def evaluate_policy(self, policy_type: str, context: EvaluationContext) -> PolicyEvaluationResult:
        """Admin simulation of one policy type; never a substitute for authorization."""
        if policy_type not in self._POLICY_TYPES:
            return self._denied("Unsupported policy type")
        return self._evaluate_policies(context, policy_type)

    def evaluate_all_policies(self, context: EvaluationContext) -> PolicyEvaluationResult:
        """Apply every active tenant policy; only access/authorization can grant access."""
        return self._evaluate_policies(context)

    def _evaluate_policies(self, context: EvaluationContext, policy_type: Optional[str] = None) -> PolicyEvaluationResult:
        try:
            policies = self.list_policies(policy_type=policy_type)
            results = []
            for policy in policies:
                if not policy.is_active:
                    continue
                if policy.tenant_id != self.tenant_id:
                    raise ValueError("Policy tenant mismatch")
                dsl = self._parse_policy_dsl(policy.policy_data)
                if dsl.type != policy.policy_type or dsl.scope != policy.scope:
                    raise ValueError("Policy metadata and DSL disagree")
                if dsl.scope_id is not None and UUID(dsl.scope_id) != policy.scope_id:
                    raise ValueError("Policy scope IDs disagree")
                if not self._policy_applies(policy, context):
                    continue
                result = self._evaluate_single_policy(policy, context)
                if result is not None:
                    results.append((policy, result))

            # Evaluate all rules/policies before combining. No grant or challenge can
            # suppress a later denial, invalid definition or unavailable fact.
            for outcome in ("deny", "require_approval", "step_up"):
                found = next((r for _, r in results if r.result == outcome), None)
                if found:
                    return found
            grant = next((r for p, r in results if r.result == "allow" and
                          (policy_type is not None or p.policy_type in {"access", "authorization"})), None)
            return grant or self._denied("No applicable explicit grant; default deny")
        except Exception:
            logger.exception("Policy evaluation failed; denying access")
            return self._denied("Policy evaluation failed or required context unavailable")

    def _policy_applies(self, policy: Policy, context: EvaluationContext) -> bool:
        if policy.scope == "tenant":
            if policy.scope_id is not None:
                raise ValueError("Tenant policy cannot have a scope ID")
            return True
        if policy.scope_id is None:
            raise ValueError("Scoped policy requires a scope ID")
        if policy.scope == "app":
            return context.resource_type == "app" and UUID(context.resource or "") == policy.scope_id
        if policy.scope == "entitlement":
            return policy.scope_id in {UUID(value) for value in context.entitlement_ids}
        raise ValueError("Unsupported policy scope")

    @classmethod
    def _parse_policy_dsl(cls, data: Dict[str, Any]) -> PolicyDSL:
        dsl = PolicyDSL.model_validate(data)
        if not dsl.rules or len({r.id for r in dsl.rules}) != len(dsl.rules):
            raise ValueError("Policy requires uniquely identified rules")
        for rule in dsl.rules:
            if not rule.id or not rule.actions:
                raise ValueError("Rule requires an ID and actions")
            for action in rule.actions:
                if action.type not in cls._ACTIONS:
                    raise ValueError("Unsupported policy action")
            for condition in rule.conditions:
                if condition.type not in cls._CONTEXT_FIELDS or condition.op not in cls._OPERATORS or condition.field is not None:
                    raise ValueError("Unsupported condition")
                if condition.value is None:
                    raise ValueError("Missing condition operand")
                if condition.op in {"in", "not_in"} and not isinstance(condition.value, list):
                    raise ValueError("Membership operand must be a list")
        return dsl

    def _evaluate_single_policy(self, policy: Policy, context: EvaluationContext) -> Optional[PolicyEvaluationResult]:
        dsl = self._parse_policy_dsl(policy.policy_data)
        matches = [rule for rule in dsl.rules if self._evaluate_rule(rule, context)]
        actions = [action for rule in matches for action in rule.actions]
        types = {action.type for action in actions}
        outcome = next((result for names, result in (
            ({"deny"}, "deny"), ({"require_approval"}, "require_approval"),
            ({"require_mfa", "require_webauthn"}, "step_up"), ({"allow"}, "allow")
        ) if types.intersection(names)), None)
        if outcome is None:
            return None
        return PolicyEvaluationResult(result=outcome, policy_id=policy.id,
                                      matched_rules=[r.id for r in matches], actions=actions,
                                      explanation=f"Policy '{policy.display_name}': {outcome}")

    def _evaluate_rule(self, rule: PolicyRule, context: EvaluationContext) -> bool:
        # Evaluate each condition, even after a false one, to expose unavailable
        # facts/invalid operands rather than silently dropping a restrictive rule.
        return all([self._evaluate_condition(c, context) for c in rule.conditions])

    def _evaluate_condition(self, condition: Condition, context: EvaluationContext) -> bool:
        actual = self._get_context_value(condition.type, context)
        if actual is None:
            raise ValueError("Required policy fact unavailable")
        op, expected = condition.op, condition.value
        if op in {"equals", "not_equals"}:
            if type(actual) is not type(expected):
                raise ValueError("Incompatible comparison types")
            return actual == expected if op == "equals" else actual != expected
        if op in {"includes", "contains"}:
            if isinstance(actual, list):
                if any(type(v) is not type(expected) for v in actual):
                    raise ValueError("Incompatible membership types")
            elif not (isinstance(actual, str) and isinstance(expected, str)):
                raise ValueError("Unsupported membership types")
            return expected in actual
        if op in {"in", "not_in"}:
            if not isinstance(expected, list) or any(type(v) is not type(actual) for v in expected):
                raise ValueError("Incompatible membership types")
            return actual in expected if op == "in" else actual not in expected
        if op in {"greater_than", "less_than"}:
            if isinstance(actual, bool) or isinstance(expected, bool) or not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
                raise ValueError("Ordered comparison requires numeric values")
            return actual > expected if op == "greater_than" else actual < expected
        raise ValueError("Unsupported policy operator")

    def _get_context_value(self, condition_type: str, context: EvaluationContext) -> Any:
        field = self._CONTEXT_FIELDS.get(condition_type)
        if field is None:
            raise ValueError("Unsupported policy fact")
        return getattr(context, field)

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

            query = f"""
                SELECT id, name, display_name, description, policy_type, template_data, is_system, category, created_at, updated_at, tenant_id
                FROM policy_templates WHERE tenant_id = :tenant_id {policy_filter}
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
                    raise HTTPException(status_code=503, detail="Policy template data is invalid") from row_error
            
            logger.info(f"Loaded {len(templates)} policy templates (policy_type={policy_type})")
            return templates
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=503, detail="Policy templates could not be loaded") from error

    def _get_sg_admin_tenant_id(self) -> Optional[UUID]:
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
        raise HTTPException(status_code=503, detail="Shared policy publication and cloning require explicit admission")

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
        raise HTTPException(status_code=503, detail="Shared policy publication and cloning require explicit admission")
    
    def _validate_policy_dsl(self, policy_data: Dict[str, Any]) -> bool:
        """Reject unsupported DSL at authoring time and again during evaluation."""
        try:
            self._parse_policy_dsl(policy_data)
            return True
        except Exception:
            return False

    def _extract_and_store_rules(self, policy_id: UUID, policy_data: Dict[str, Any]):
        """Replace child rows inside the caller's transaction; never swallow failure."""
        policy_dsl = self._parse_policy_dsl(policy_data)
        params = {"policy_id": str(policy_id), "tenant_id": str(self.tenant_id)}
        parent = self.db.execute(text(
            "SELECT id FROM policies WHERE id=:policy_id AND tenant_id=:tenant_id FOR UPDATE"
        ), params).first()
        if parent is None:
            raise ValueError("Policy is not available in this tenant")
        self.db.execute(text("DELETE FROM policy_rules WHERE policy_id=:policy_id"),
                        {"policy_id": str(policy_id)})
        for rule in policy_dsl.rules:
            self.db.execute(text("""
                INSERT INTO policy_rules (policy_id, rule_id, name, description, conditions, actions, priority, is_active)
                VALUES (:policy_id, :rule_id, :name, :description, CAST(:conditions AS jsonb), CAST(:actions AS jsonb), :priority, true)
            """), {
                "policy_id": str(policy_id), "rule_id": rule.id,
                "name": rule.name, "description": rule.description,
                "conditions": json.dumps([c.model_dump(mode="json") for c in rule.conditions]),
                "actions": json.dumps([a.model_dump(mode="json") for a in rule.actions]),
                "priority": rule.priority,
            })

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
