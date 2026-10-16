import pytest
from httpx import AsyncClient
from app.main import app
from app.services.framework_mapper import FrameworkMapper


@pytest.mark.asyncio
async def test_soc2_mapping_includes_expected_keys():
    mapper = FrameworkMapper()
    incident = {"category": "login_failure", "severity": "high"}
    result = await mapper.map_incident(incident)
    assert "soc2_criteria" in result
    assert any(item["criterion_id"] == "CC6.1" for item in result["soc2_criteria"])


@pytest.mark.asyncio
async def test_soc2_endpoint_lookup():
    mapper = FrameworkMapper()
    crit = mapper.soc2_mapper.get_criterion("CC6.1")
    assert crit.get("criterion_id") == "CC6.1"
