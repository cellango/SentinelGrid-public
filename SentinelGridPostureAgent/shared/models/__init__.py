"""SQLAlchemy models for posture platform."""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import models for Alembic autogenerate
from .observable import Observable  # noqa
from .asset import Asset  # noqa
from .finding import Finding  # noqa
from .analyzer_job import AnalyzerJob  # noqa
from .posture_score import PostureScore  # noqa
from .cloud_account import CloudAccount  # noqa
from .repository import Repository  # noqa

