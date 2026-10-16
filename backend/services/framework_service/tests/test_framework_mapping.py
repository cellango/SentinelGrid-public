"""
Tests for Framework Mapping Service (NIST/MITRE).
"""

import pytest
from app.services.nist_mapper import NISTMapper
from app.services.mitre_mapper import MITREMapper
from app.services.framework_mapper import FrameworkMapper


class TestFrameworkMapping:
    """Tests for framework mapping."""
    
    @pytest.mark.asyncio
    async def test_nist_mapping(self):
        """Test NIST control mapping."""
        mapper = NISTMapper()
        
        incident_data = {
            "category": "suspicious_login",
            "severity": "high"
        }
        
        controls = await mapper.map_incident_to_controls(incident_data)
        
        assert len(controls) > 0
        assert any(c["control_id"] == "IR-4" for c in controls)  # Always included
        assert any(c["control_id"] == "AC-2" for c in controls)  # Login-related
    
    @pytest.mark.asyncio
    async def test_mitre_mapping(self):
        """Test MITRE mapping."""
        mapper = MITREMapper()
        
        incident_data = {
            "category": "malware"
        }
        
        mapping = await mapper.map_incident_to_mitre(incident_data)
        
        assert "tactics" in mapping
        assert "techniques" in mapping
        assert len(mapping["tactics"]) > 0
        assert len(mapping["techniques"]) > 0
    
    @pytest.mark.asyncio
    async def test_framework_mapper_integration(self):
        """Test integrated framework mapper."""
        mapper = FrameworkMapper()
        
        incident_data = {
            "category": "phishing",
            "severity": "high"
        }
        
        result = await mapper.map_incident(incident_data)
        
        assert "nist_controls" in result
        assert "mitre_tactics" in result
        assert "mitre_techniques" in result
        assert len(result["nist_controls"]) > 0
        assert len(result["mitre_tactics"]) > 0

