"""Database configuration for Reporting Service."""

import os
import sys
from typing import Generator

from sqlalchemy.orm import Session

# Add libs directory to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)
else:
    sys.path.insert(0, "/app/libs")

from sg_core.db import Base, engine, get_db, get_tenant_db, get_tenant_session
from sg_core.security import get_current_tenant

# Import reporting-specific models to register them with Base
from app.models.report import Report, ReportTemplate, ReportShare

# Note: Tables are created via migrations or on first import
# Base.metadata.create_all(bind=engine)  # Uncomment if needed for development

__all__ = [
    "get_db",
    "get_tenant_db",
    "get_tenant_session",
    "get_current_tenant",
    "Session",
    "Base",
    "engine",
]
