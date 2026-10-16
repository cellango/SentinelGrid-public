from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_config_module():
    path = Path(__file__).resolve().parents[1] / "app" / "core" / "config.py"
    spec = importlib.util.spec_from_file_location("ai_shield_config_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_production_rejects_default_internal_service_token(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("INTERNAL_SERVICE_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="INTERNAL_SERVICE_TOKEN"):
        _load_config_module()
