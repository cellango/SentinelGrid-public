"""Model Gateway client for orchestrator."""

import logging
import httpx
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelGatewayClient:
    """Client for interacting with Model Gateway."""
    
    def __init__(self):
        self.base_url = settings.MODEL_GATEWAY_URL
        self.token = settings.INTERNAL_SERVICE_TOKEN
        self.timeout = settings.SERVICE_TIMEOUT * 2  # AI calls may take longer
    
    async def generate_snapshot_analysis(
        self,
        tenant_id: str,
        snapshot_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate AI analysis for security snapshot.
        
        Args:
            tenant_id: Tenant ID
            snapshot_data: Snapshot data to analyze
        
        Returns:
            AI analysis dictionary
        """
        try:
            # Prepare prompt for snapshot analysis
            prompt = self._build_snapshot_prompt(snapshot_data)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use unified chat endpoint for analysis
                response = await client.post(
                    f"{self.base_url}/internal/llm/chat",
                    json={
                        "query": prompt,
                        "tenant_id": tenant_id,
                        "context": {"type": "security_snapshot"},
                    },
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "X-Tenant-ID": tenant_id,
                    },
                )
                response.raise_for_status()
                result = response.json()
                
                # Parse AI response
                return self._parse_ai_response(result, snapshot_data)
        
        except Exception as e:
            logger.error(f"Error generating AI analysis: {e}")
            return self._get_fallback_analysis(
                snapshot_data,
                error="AI analysis unavailable. Review live alerts and recommendations directly.",
            )
    
    def _build_snapshot_prompt(self, snapshot_data: Dict[str, Any]) -> str:
        """Build prompt for AI snapshot analysis."""
        events_count = snapshot_data.get("summary", {}).get("events_count", 0)
        alerts_count = snapshot_data.get("summary", {}).get("alerts_count", 0)
        users_count = snapshot_data.get("summary", {}).get("users_active", 0)
        
        alerts = snapshot_data.get("top_findings", [])
        alerts_summary = "\n".join([
            f"- {alert.get('title', 'Unknown')} ({alert.get('severity', 'unknown')})"
            for alert in alerts[:5]
        ])
        
        prompt = f"""Analyze this security snapshot for a tenant and provide:

1. **Security Posture Summary**: Overall assessment (Good/Needs Attention/At Risk)
2. **Key Findings**: Top 3-5 most critical security concerns
3. **Recommendations**: Actionable recommendations prioritized by urgency
4. **Risk Level**: Low/Medium/High/Critical

**Snapshot Data:**
- Events Processed: {events_count:,}
- Active Alerts: {alerts_count}
- Active Users: {users_count}

**Top Alerts:**
{alerts_summary if alerts_summary else "No alerts"}

Provide a concise, actionable analysis in JSON format:
{{
  "posture": "Good|Needs Attention|At Risk",
  "risk_level": "Low|Medium|High|Critical",
  "key_findings": ["finding1", "finding2", ...],
  "recommendations": [
    {{"priority": "High|Medium|Low", "action": "recommendation text"}},
    ...
  ],
  "summary": "Brief summary paragraph"
}}"""
        
        return prompt
    
    def _parse_ai_response(self, result: Dict[str, Any], snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response into structured analysis."""
        import json
        import re
        
        try:
            # Extract content from response
            content = result.get("response", "") or result.get("content", "") or result.get("message", "")
            
            # Extract JSON from response (may have markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                analysis_json = json.loads(json_match.group())
                return {
                    "posture": analysis_json.get("posture", "Unknown"),
                    "risk_level": analysis_json.get("risk_level", "Medium"),
                    "key_findings": analysis_json.get("key_findings", []),
                    "recommendations": analysis_json.get("recommendations", []),
                    "summary": analysis_json.get("summary", ""),
                    "raw_response": content,
                }
            
            return self._get_fallback_analysis(
                snapshot_data,
                error="AI analysis returned an unstructured response and was not applied.",
                raw_response=content,
            )
        
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._get_fallback_analysis(
                snapshot_data,
                error="AI analysis could not be parsed and was not applied.",
            )
    
    def _get_fallback_analysis(
        self,
        snapshot_data: Dict[str, Any],
        *,
        error: str,
        raw_response: str | None = None,
    ) -> Dict[str, Any]:
        """Return an explicit unavailable state instead of synthetic AI guidance."""
        return {
            "posture": "Unknown",
            "risk_level": "Unknown",
            "key_findings": [],
            "recommendations": [],
            "summary": error,
            "raw_response": raw_response,
            "error": error,
            "analysis_available": False,
        }
    
    async def analyze_phishing_email(
        self,
        tenant_id: str,
        email_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a phishing email using AI.
        
        Args:
            tenant_id: Tenant ID
            email_content: Email content dictionary (from, subject, body, etc.)
            
        Returns:
            AI analysis dictionary with classification, confidence, reasoning, etc.
        """
        try:
            # Build phishing analysis prompt
            prompt = self._build_phishing_prompt(email_content)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/internal/llm/chat",
                    json={
                        "query": prompt,
                        "tenant_id": tenant_id,
                        "context": {"type": "phishing_analysis"},
                    },
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "X-Tenant-ID": tenant_id,
                    },
                )
                response.raise_for_status()
                result = response.json()
                
                # Parse AI response
                return self._parse_phishing_response(result, email_content)
        
        except Exception as e:
            logger.error(f"Error analyzing phishing email: {e}")
            return self._get_fallback_phishing_analysis(
                error="AI analysis unavailable. Manual review is required before classifying this email.",
            )
    
    def _build_phishing_prompt(self, email_content: Dict[str, Any]) -> str:
        """Build prompt for phishing email analysis."""
        from_addr = email_content.get("from_address", "Unknown")
        subject = email_content.get("subject", "")
        text_body = email_content.get("text_body", "")
        html_body = email_content.get("html_body", "")
        attachments = email_content.get("attachments", [])
        
        # Use text body if available, otherwise HTML
        email_body = text_body or (html_body[:1000] if html_body else "")
        
        attachments_str = ", ".join([att.get("filename", "unknown") for att in attachments]) if attachments else "None"
        
        prompt = f"""You are a cybersecurity analyst specializing in phishing email detection.

Analyze the following email and determine if it is:
1. Phishing (malicious attempt to steal credentials/data)
2. Benign (legitimate email)
3. Suspicious (unclear, needs human review)

Email Details:
- From: {from_addr}
- Subject: {subject}
- Body: {email_body[:2000]}  # Truncated for prompt
- Attachments: {attachments_str}

Provide your analysis in JSON format:
{{
  "classification": "phishing|benign|suspicious",
  "confidence": 0-100,
  "reasoning": "Detailed explanation of why you classified it this way",
  "indicators": {{
    "urls": ["list of URLs found"],
    "domains": ["list of domains"],
    "ips": ["list of IP addresses"],
    "email_addresses": ["list of email addresses"]
  }},
  "recommended_actions": [
    "Action 1",
    "Action 2",
    ...
  ],
  "mitre_mapping": {{
    "tactics": ["TA0001", "TA0004"],
    "techniques": ["T1566", "T1566.001"]
  }},
  "nist_mapping": {{
    "controls": ["AT-2", "IR-4", "SI-4"]
  }}
}}

Focus on:
- Suspicious URLs or domains (lookalike domains, shortened URLs)
- Urgency tactics (urgent action required, account suspension)
- Social engineering (requests for credentials, personal information)
- Suspicious attachments
- Sender reputation (unknown sender, spoofed address)
"""
        return prompt
    
    def _parse_phishing_response(
        self,
        result: Dict[str, Any],
        email_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse AI response for phishing analysis."""
        try:
            # Extract content from response
            content = result.get("response", "") or result.get("content", "") or result.get("message", "")
            
            # Try to parse JSON from content
            import json
            import re
            
            # Extract JSON from response (may have markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                analysis_json = json.loads(json_match.group())
                return {
                    "classification": analysis_json.get("classification", "suspicious").lower(),
                    "confidence": float(analysis_json.get("confidence", 50)),
                    "reasoning": analysis_json.get("reasoning", ""),
                    "indicators": analysis_json.get("indicators", {}),
                    "recommended_actions": analysis_json.get("recommended_actions", []),
                    "mitre_mapping": analysis_json.get("mitre_mapping", {}),
                    "nist_mapping": analysis_json.get("nist_mapping", {}),
                    "raw_response": content,
                }
            
            return self._get_fallback_phishing_analysis(
                error="AI analysis returned an unstructured response. Manual review is required before classifying this email.",
                raw_response=content,
            )
        
        except Exception as e:
            logger.error(f"Error parsing phishing analysis response: {e}")
            return self._get_fallback_phishing_analysis(
                error="AI analysis could not be parsed. Manual review is required before classifying this email.",
            )
    
    def _get_fallback_phishing_analysis(
        self,
        *,
        error: str,
        raw_response: str | None = None,
    ) -> Dict[str, Any]:
        """Return an explicit manual-review state instead of heuristic AI output."""
        return {
            "classification": "pending",
            "confidence": 0.0,
            "reasoning": error,
            "indicators": {},
            "recommended_actions": [
                "Review the email manually before changing classification or severity.",
                "Validate sender, links, and attachments using live tooling.",
            ],
            "mitre_mapping": {},
            "nist_mapping": {},
            "raw_response": raw_response,
            "error": error,
            "analysis_available": False,
        }
