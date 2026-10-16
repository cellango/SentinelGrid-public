"""
Report Q&A Prompts
Specialized prompts for compliance report querying
"""

from typing import List


def get_report_qa_prompt(query: str, context_chunks: List[str]) -> str:
    """
    Generate prompt for report Q&A.
    
    Args:
        query: User query
        context_chunks: Relevant report sections
        
    Returns:
        Formatted prompt
    """
    context = "\n\n---\n\n".join([
        f"Report Section {i+1}:\n{chunk}"
        for i, chunk in enumerate(context_chunks)
    ])
    
    return f"""You are an expert compliance analyst assistant helping users understand their security compliance reports. Answer the user's question based ONLY on the provided report sections.

COMPLIANCE REPORT CONTEXT:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
1. Answer based EXCLUSIVELY on the provided report sections
2. If the information is not in the reports, clearly state: "This information is not available in your current compliance reports."
3. Be specific and cite relevant metrics, percentages, or findings
4. Use professional language appropriate for compliance and security contexts
5. If multiple reports are mentioned, specify which report contains the information
6. For numerical data, provide exact values from the reports
7. For compliance status, use clear terms: "Compliant", "Non-Compliant", "Partially Compliant", "In Progress"

ANSWER:"""


def get_soc2_specific_prompt(query: str, context_chunks: List[str]) -> str:
    """Prompt for SOC 2 specific questions."""
    context = "\n\n".join(context_chunks)
    
    return f"""You are a SOC 2 compliance expert. Answer the question about SOC 2 Trust Services Criteria based on the provided compliance report.

SOC 2 REPORT CONTEXT:
{context}

QUESTION: {query}

Focus on Trust Services Criteria (CC1-CC9) and provide specific control coverage status.

ANSWER:"""


def get_nist_specific_prompt(query: str, context_chunks: List[str]) -> str:
    """Prompt for NIST CSF specific questions."""
    context = "\n\n".join(context_chunks)
    
    return f"""You are a NIST Cybersecurity Framework expert. Answer the question about NIST CSF implementation based on the compliance report.

NIST CSF REPORT CONTEXT:
{context}

QUESTION: {query}

Focus on the five NIST CSF functions (Identify, Protect, Detect, Respond, Recover) and implementation status.

ANSWER:"""


def get_iam_mfa_prompt(query: str, context_chunks: List[str]) -> str:
    """Prompt for IAM/MFA hygiene questions."""
    context = "\n\n".join(context_chunks)
    
    return f"""You are an Identity and Access Management (IAM) expert. Answer the question about IAM hygiene and MFA coverage based on the compliance report.

IAM/MFA REPORT CONTEXT:
{context}

QUESTION: {query}

Provide specific metrics like MFA coverage %, privileged users count, dormant accounts, etc.

ANSWER:"""


def get_incident_response_prompt(query: str, context_chunks: List[str]) -> str:
    """Prompt for incident response questions."""
    context = "\n\n".join(context_chunks)
    
    return f"""You are an incident response analyst. Answer the question about incident handling and response effectiveness based on the compliance report.

INCIDENT RESPONSE REPORT CONTEXT:
{context}

QUESTION: {query}

Include metrics like MTTD, MTTR, incident counts, and playbook effectiveness.

ANSWER:"""


def get_summary_prompt(report_type: str) -> str:
    """Get prompt for report summarization."""
    return f"""Provide a concise executive summary of this {report_type} compliance report.

Focus on:
1. Overall compliance status/score
2. Key findings (top 3-5)
3. Critical gaps or issues requiring attention
4. Positive highlights
5. Recommended actions

Keep the summary professional and suitable for executive-level review (200-300 words)."""

