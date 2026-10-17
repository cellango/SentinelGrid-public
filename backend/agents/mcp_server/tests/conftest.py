"""Isolated source/protocol checks: real MCP SDK, no downstream services."""

import socket
import sys
from pathlib import Path
import httpx
import pytest
import psycopg2
from sqlalchemy.engine import Engine

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "libs"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def reject_downstream_effects(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail(
            "MCP source test attempted a downstream client, network or database effect"
        )

    monkeypatch.setattr(httpx.Client, "__init__", blocked)
    monkeypatch.setattr(httpx.AsyncClient, "__init__", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(psycopg2, "connect", blocked)
    monkeypatch.setattr(Engine, "connect", blocked)
