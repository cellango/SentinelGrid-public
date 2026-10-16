"""
Unified Chat Service
Single chat interface for all modules (IAM, SOC, SIEM)
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)
ModelService = None
RAGService = None


class UnifiedChatService:
    """Service for unified chat across all SentinelGrid modules."""
    
    def __init__(self):
        self.module_keywords = {
            "iam": ["user", "role", "permission", "access", "policy", "identity", "authentication", "authorization", "entitlement"],
            "soc": ["incident", "playbook", "alert", "triage", "response", "respond", "investigation", "threat", "malware", "phishing"],
            "siem": ["log", "event", "correlation", "detection", "query", "search", "analytics", "security event"],
            "compliance": [
                "compliance",
                "soc 2",
                "soc2",
                "audit",
                "framework",
                "control",
                "evidence",
                "gap",
                "report",
                "attestation",
                "hipaa",
                "pci",
                "iso 27001",
                "nist 800-171",
            ],
        }
    
    def process_chat_query(
        self,
        query: str,
        tenant_id: str,
        module: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat query across all modules.
        
        Args:
            query: User query
            tenant_id: Tenant ID
            module: Explicit module (optional, will auto-detect if not provided)
            context: Additional context (current incident, policy, etc.)
            
        Returns:
            Chat response with module-specific context
        """
        # Auto-detect module if not specified
        if not module:
            module = self._detect_module(query, context)
        
        # Get module-specific context
        module_context = self._get_module_context(tenant_id, module, context)
        
        # Retrieve RAG context
        rag_context = self._retrieve_rag_context(tenant_id, module, query)
        
        # Build prompt
        prompt = self._build_unified_prompt(query, module, module_context, rag_context, tenant_id)
        retrieval_categories = self._retrieval_categories_for_module(module, module_context)
        proposed_actions = self._build_proposed_actions(module, module_context)
        source_kind = self._source_kind_for_module(module, module_context, proposed_actions, rag_context)
        answer_type = source_kind
        
        # Store prompt for model service to use
        return {
            "prompt": prompt,
            "module": module,
            "tenant_id": tenant_id,
            "sources": rag_context.get("sources", []),
            "confidence": 0.8,  # Default confidence
            "generated_at": datetime.utcnow().isoformat(),
            "answer_type": answer_type,
            "source_kind": source_kind,
            "retrieval_categories": retrieval_categories,
            "actions": proposed_actions,
        }
    
    def _detect_module(self, query: str, context: Optional[Dict[str, Any]]) -> str:
        """Auto-detect module from query or context."""
        # Check context first
        if context:
            active_agent = context.get("active_agent")
            dashboard_data = context.get("dashboard_data") if isinstance(context.get("dashboard_data"), dict) else {}
            if active_agent == "compliance_agent" or dashboard_data.get("active_agent") == "compliance_agent":
                return "compliance"
            if context.get("compliance_live_context"):
                return "compliance"
            if context.get("current_incident_id"):
                return "soc"
            if context.get("current_policy_id"):
                return "iam"
            if context.get("log_query"):
                return "siem"
        
        # Detect from query keywords
        query_lower = query.lower()
        if query_lower.startswith("/compliance"):
            return "compliance"
        
        scores = {
            module_name: sum(1 for keyword in keywords if keyword in query_lower)
            for module_name, keywords in self.module_keywords.items()
        }
        
        # Return module with highest score, default to "iam"
        detected_module = max(scores.items(), key=lambda x: x[1])[0]
        
        # If no strong signal, use general
        if scores[detected_module] == 0:
            return "general"
        
        return detected_module
    
    def _get_module_context(
        self,
        tenant_id: str,
        module: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get module-specific context."""
        module_context = {
            "module": module,
            "tenant_id": tenant_id
        }
        
        if context:
            module_context.update(context)
        
        # Add module-specific context
        if module == "iam":
            # Could fetch current user, policy, etc.
            pass
        elif module == "soc":
            # Could fetch current incident, playbook, etc.
            pass
        elif module == "siem":
            # Could fetch current log query, dashboard, etc.
            pass
        elif module == "compliance":
            compliance_context = module_context.get("compliance_live_context") or {}
            module_context["retrieval_categories"] = compliance_context.get("retrieval_categories", [])
            module_context["accessed_categories"] = compliance_context.get("accessed_categories", [])
        
        return module_context
    
    def _retrieve_rag_context(
        self,
        tenant_id: str,
        module: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Retrieve RAG context from tenant-specific vector database.
        
        Args:
            tenant_id: Tenant ID
            module: Module (iam, soc, siem)
            query: User query
            
        Returns:
            Dictionary with sources and context text
        """
        # Map module to knowledge base categories
        module_to_category = {
            "iam": ["nist", "cis"],  # IAM-related frameworks
            "soc": ["mitre", "playbook", "nist"],  # SOC-related
            "siem": ["mitre", "cve", "nist"],  # SIEM-related
            "compliance": ["reports", "controls", "evidence", "gaps"],
        }
        
        categories = module_to_category.get(module, None)
        
        try:
            # Import RAG service lazily (avoid circular imports and keep tests patchable)
            rag_service_cls = RAGService
            if rag_service_cls is None:
                from app.services.rag_service import RAGService as rag_service_cls
            from app.core.database import SessionLocal
            
            # Create DB session for RAG
            db = SessionLocal()
            try:
                rag_service = rag_service_cls(db_session=db)
                
                # Search in relevant categories
                all_sources = []
                for category in categories if categories else [None]:
                    results = rag_service.search(
                        query=query,
                        tenant_id=tenant_id,
                        category=category,
                        top_k=3  # 3 per category
                    )
                    all_sources.extend(results)
                
                # Sort by similarity and take top 3 to keep prompts small/fast
                all_sources.sort(key=lambda x: x.get("similarity", 0), reverse=True)
                top_sources = all_sources[:3]
                
                # Build context text
                context_parts = []
                for i, source in enumerate(top_sources, 1):
                    snippet = (source.get("content") or "")[:400]
                    title = source.get("title") or "Reference"
                    category = source.get("category") or "knowledge_base"
                    context_parts.append(f"[{i}] {title} ({category}):\n{snippet}")
                
                context = "\n\n".join(context_parts)
                
                return {
                    "sources": top_sources,
                    "context": context
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error retrieving RAG context: {e}")
            return {
                "sources": [],
                "context": ""
            }
    
    def _build_unified_prompt(
        self,
        query: str,
        module: str,
        module_context: Dict[str, Any],
        rag_context: Dict[str, Any],
        tenant_id: str
    ) -> str:
        """Build unified prompt for all modules."""
        prompt_parts = [
            "You are SentinelGrid AI Assistant, a cybersecurity expert for all security operations.",
            "",
            "Available Modules:",
            "- IAM: Identity and Access Management, policies, roles, permissions",
            "- SOC: Security Operations Center, incidents, playbooks, threat response",
            "- SIEM: Security Information and Event Management, logs, events, detection",
            "- Compliance: frameworks, controls, evidence, reports, and control gaps",
            "",
            f"Current Module: {module.upper()}",
            f"Tenant: {tenant_id}",
            ""
        ]
        
        # Add module-specific instructions
        if module == "iam":
            prompt_parts.extend([
                "Focus on: Access control, user management, role-based access, policies, entitlements, compliance (NIST, etc.)",
                ""
            ])
        elif module == "soc":
            prompt_parts.extend([
                "Focus on: Incident response, threat detection, playbooks, MITRE ATT&CK, security operations",
                ""
            ])
        elif module == "siem":
            prompt_parts.extend([
                "Focus on: Log analysis, event correlation, security event detection, querying, analytics",
                ""
            ])
        elif module == "compliance":
            prompt_parts.extend([
                "Focus on: Live compliance posture, selected frameworks, control coverage, evidence state, report state, and open gaps.",
                "Do not present a generic model answer as an audit-ready compliance determination.",
                "When live context is present, identify it as live status and call out that human review is required for audit use.",
                "When only knowledge base context is present, state that it is reference guidance rather than tenant-specific compliance status.",
                "",
            ])

            live_context = module_context.get("compliance_live_context") or {}
            if live_context:
                prompt_parts.extend([
                    "Live Compliance Context:",
                    json.dumps(live_context, default=str)[:4000],
                    "",
                ])
        
        # Add RAG context
        if rag_context.get("context"):
            prompt_parts.extend([
                "Relevant Context:",
                rag_context["context"],
                ""
            ])
        
        # Add user query
        prompt_parts.extend([
            "User Query:",
            query,
            "",
            "Provide a helpful, accurate answer:"
        ])
        
        return "\n".join(prompt_parts)

    def _retrieval_categories_for_module(self, module: str, module_context: Dict[str, Any]) -> List[str]:
        if module == "compliance":
            live_context = module_context.get("compliance_live_context") or {}
            categories = live_context.get("retrieval_categories") or ["reports", "controls", "evidence", "gaps"]
            return [str(category) for category in categories]
        return []

    def _build_proposed_actions(self, module: str, module_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if module != "compliance":
            return []

        live_context = module_context.get("compliance_live_context") or {}
        recommendations = live_context.get("recommendations") or {}
        items = recommendations.get("items") if isinstance(recommendations, dict) else []
        actions = []
        for item in (items or [])[:3]:
            if not isinstance(item, dict):
                continue
            actions.append(
                {
                    "label": item.get("title") or "Review Compliance Agent recommendation",
                    "action": "review_compliance_agent_recommendation",
                    "endpoint": "/api/v1/compliance/agent/recommendations",
                    "recommendation_id": item.get("id"),
                    "requires_approval": item.get("recommendation_type") != "read_only_summary",
                }
            )
        if not actions and module_context.get("active_agent") == "compliance_agent":
            actions.append(
                {
                    "label": "Review Compliance Agent recommendations",
                    "action": "open_compliance_agent_recommendations",
                    "endpoint": "/api/v1/compliance/agent/recommendations",
                    "requires_approval": False,
                }
            )
        return actions

    def _source_kind_for_module(
        self,
        module: str,
        module_context: Dict[str, Any],
        proposed_actions: List[Dict[str, Any]],
        rag_context: Dict[str, Any],
    ) -> str:
        if module == "compliance":
            live_context = module_context.get("compliance_live_context") or {}
            if proposed_actions and live_context:
                return "proposed_agent_action"
            if live_context:
                return "live_compliance_status"
            if rag_context.get("sources"):
                return "knowledge_base"
        return "knowledge_base" if rag_context.get("sources") else "general"
    
    def _generate_response(
        self,
        tenant_id: str,
        prompt: str,
        module: str
    ) -> Dict[str, Any]:
        """
        Generate response using Model Gateway with tenant adapter.
        
        Would call Model Gateway service which:
        1. Loads base model
        2. Loads tenant LoRA adapter
        3. Merges adapter weights
        4. Generates response
        """
        # TODO: Implement actual model call
        # For now, return placeholder
        return {
            "text": "Response would be generated here",
            "confidence": 0.8,
            "model": "cybergpt-7b",
            "adapter_used": f"tenant-{tenant_id}"
        }
