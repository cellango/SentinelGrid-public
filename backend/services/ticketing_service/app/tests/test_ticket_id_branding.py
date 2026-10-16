import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from app.services.ticket_service import TicketService


def make_db():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE tenants (
                    id TEXT PRIMARY KEY,
                    slug TEXT
                );
                CREATE TABLE tickets (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT,
                    tenant_slug TEXT,
                    title TEXT,
                    description TEXT,
                    status TEXT,
                    severity TEXT,
                    priority TEXT,
                    category TEXT,
                    source TEXT,
                    external_id TEXT,
                    external_vendor_id TEXT,
                    cve_ids TEXT,
                    exploit_indicators TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                """
            )
        )
        conn.execute(text("INSERT INTO tenants (id, slug) VALUES (:id, :slug)"), {"id": "tid-1", "slug": "acme"})
        conn.commit()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_ticket_public_id_prefix():
    db = make_db()
    svc = TicketService()
    tenant_id = "tid-1"
    ticket_data = {"title": "Test Ticket", "tenant_slug": "acme"}
    # Patch models import for sqlite table; emulate minimal Ticket model via direct insert
    # For this unit test, just call _generate_public_id
    public_id = svc._generate_public_id("acme")
    assert public_id.startswith("SG-acme-")


def test_ticket_public_id_defaults_when_slug_missing():
    svc = TicketService()
    public_id = svc._generate_public_id(None)
    assert public_id.startswith("SG-tenant-")


def test_ticket_public_id_sanitizes_slug():
    svc = TicketService()
    public_id = svc._generate_public_id("ACME INC!!")
    assert public_id.startswith("SG-acme-inc-")
