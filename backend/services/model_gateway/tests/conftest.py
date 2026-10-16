"""
Pytest configuration and fixtures for Model Gateway tests.
"""

import pytest
import os
import sys
import uuid
import tempfile
import types
import importlib.util
from typing import Generator
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Ensure project paths are on sys.path for imports in CI
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[3]
MODEL_GATEWAY_ROOT = REPO_ROOT / "backend" / "services" / "model_gateway"
sys.path.insert(0, str(MODEL_GATEWAY_ROOT))
sys.path.insert(0, str(MODEL_GATEWAY_ROOT / "app"))
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))


if importlib.util.find_spec("redis") is None:
    redis_stub = types.ModuleType("redis")

    class _DummyRedisConnection:
        def ping(self):
            return True

    def _from_url(*args, **kwargs):
        return _DummyRedisConnection()

    redis_stub.from_url = _from_url
    sys.modules["redis"] = redis_stub


if importlib.util.find_spec("rq") is None:
    rq_stub = types.ModuleType("rq")
    rq_job_stub = types.ModuleType("rq.job")

    class _DummyRegistry:
        count = 0

    class _DummyJob:
        id = "stub-job"
        created_at = None
        started_at = None
        ended_at = None
        meta = {}
        result = None
        exc_info = None
        is_finished = False
        is_failed = False

        def get_status(self):
            return "queued"

        def cancel(self):
            return None

        @staticmethod
        def fetch(*args, **kwargs):
            return _DummyJob()

    class _DummyQueue:
        started_job_registry = _DummyRegistry()
        finished_job_registry = _DummyRegistry()
        failed_job_registry = _DummyRegistry()

        def __init__(self, *args, **kwargs):
            pass

        def enqueue(self, *args, **kwargs):
            return _DummyJob()

        def __len__(self):
            return 0

    rq_stub.Queue = _DummyQueue
    rq_job_stub.Job = _DummyJob
    rq_job_stub.JobStatus = type("JobStatus", (), {})
    sys.modules["rq"] = rq_stub
    sys.modules["rq.job"] = rq_job_stub

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, get_db, get_tenant_session

# Before importing app.main (which constructs ModelService), ensure model paths are writable
for key in ["ADAPTER_STORAGE_PATH", "BASE_MODEL_PATH", "MODEL_CACHE"]:
    if not os.environ.get(key):
        os.environ[key] = tempfile.mkdtemp(prefix=f"{key.lower()}_")
    else:
        path = Path(os.environ[key])
        try:
            path.mkdir(parents=True, exist_ok=True)
            if not os.access(path, os.W_OK):
                os.environ[key] = tempfile.mkdtemp(prefix=f"{key.lower()}_")
        except Exception:
            os.environ[key] = tempfile.mkdtemp(prefix=f"{key.lower()}_")

from app.main import app as fastapi_app  # noqa: E402
import app.services.model_service as _model_service  # noqa: F401,E402


# Test database URL (use TEST_DATABASE_URL if provided)
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///./test_model_gateway.db"
)

# Ensure adapter/model paths are writable in CI; if default is not writable, use temp dirs.
default_adapter = "/tmp/models/adapters"
default_base = "/tmp/models/base"
default_cache = "/tmp/models/cache"

for env_key, default_path in [
    ("ADAPTER_STORAGE_PATH", default_adapter),
    ("BASE_MODEL_PATH", default_base),
    ("MODEL_CACHE", default_cache),
]:
    path = os.getenv(env_key, default_path)
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        if os.access(path, os.W_OK):
            os.environ.setdefault(env_key, path)
            continue
    except Exception:
        pass
    tmp_dir = tempfile.mkdtemp(prefix=f"{env_key.lower()}_")
    os.environ[env_key] = tmp_dir

# Use PostgreSQL for tests if available, otherwise SQLite
if TEST_DB_URL.startswith("postgresql"):
    engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
else:
    # SQLite for testing
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a test database session."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_tenant_id() -> str:
    """Generate a test tenant ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_training_data() -> list:
    """Sample training data for tests."""
    return [
        {
            "instruction": "You are a cybersecurity expert. Answer the question:",
            "input": "What is least privilege?",
            "output": "Least privilege is a security principle that states users and processes should only have the minimum access necessary to perform their functions."
        },
        {
            "instruction": "You are a cybersecurity expert. Answer the question:",
            "input": "What is NIST AC-2?",
            "output": "NIST AC-2 is Account Management control that requires organizations to manage user accounts, including creating, modifying, disabling, and removing accounts."
        },
        {
            "instruction": "You are a cybersecurity expert. Answer the question:",
            "input": "What is RBAC?",
            "output": "RBAC stands for Role-Based Access Control, an access control method that restricts access based on roles assigned to users."
        },
        {
            "instruction": "You are a cybersecurity expert. Answer the question:",
            "input": "What is MITRE ATT&CK?",
            "output": "MITRE ATT&CK is a globally-accessible knowledge base of adversary tactics and techniques based on real-world observations of cybersecurity threats."
        },
        {
            "instruction": "You are a cybersecurity expert. Answer the question:",
            "input": "What is OWASP Top 10?",
            "output": "OWASP Top 10 is a standard awareness document for developers and web application security, representing the most critical security risks to web applications."
        },
    ] * 2  # 10 samples total


@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    mock_conn = Mock()
    mock_conn.ping.return_value = True
    return mock_conn


@pytest.fixture
def mock_job_queue(mock_redis):
    """Mock RQ job queue."""
    with patch("app.services.job_queue.redis.from_url", return_value=mock_redis):
        with patch("app.services.job_queue.Queue") as mock_queue_class:
            mock_queue = Mock()
            mock_queue.enqueue.return_value = Mock(id="test-job-id", get_status=lambda: "queued")
            mock_queue_class.return_value = mock_queue
            yield mock_queue


@pytest.fixture
def mock_peft_available():
    """Mock PEFT library availability."""
    with patch("app.services.adapter_training_service.PEFT_AVAILABLE", True):
        with patch("app.services.peft_adapter_service.PEFT_AVAILABLE", True):
            yield


@pytest.fixture
def mock_model_loading():
    """Mock model loading to avoid downloading actual models."""
    with patch("app.services.adapter_training_service.AutoModelForCausalLM") as mock_model:
        with patch("app.services.adapter_training_service.AutoTokenizer") as mock_tokenizer:
            mock_model_instance = Mock()
            mock_tokenizer_instance = Mock()
            mock_tokenizer_instance.pad_token = None
            mock_tokenizer_instance.eos_token = "<|endoftext|>"
            mock_tokenizer_instance.eos_token_id = 50256
            
            mock_model.from_pretrained.return_value = mock_model_instance
            mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
            
            yield {
                "model": mock_model_instance,
                "tokenizer": mock_tokenizer_instance
            }


@pytest.fixture
def mock_trainer():
    """Mock HuggingFace Trainer."""
    with patch("app.services.adapter_training_service.Trainer") as mock_trainer_class:
        mock_trainer_instance = Mock()
        mock_trainer_instance.train.return_value = Mock(
            training_loss=0.5,
            metrics={"train_runtime": 3600, "train_samples_per_second": 0.5}
        )
        mock_trainer_instance.evaluate.return_value = {"eval_loss": 0.6}
        mock_trainer_instance.state.log_history = [{"loss": 0.5}]
        mock_trainer_class.return_value = mock_trainer_instance
        yield mock_trainer_instance


@pytest.fixture
def override_get_db(db_session):
    """Override get_db dependency with test session."""
    def _get_db():
        try:
            yield db_session
        finally:
            pass  # Don't close session in tests

    def _get_tenant_session():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _get_db
    fastapi_app.dependency_overrides[get_tenant_session] = _get_tenant_session
    yield
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db):
    """Create test client."""
    return TestClient(fastapi_app)


@pytest.fixture
def test_adapter_storage_path(tmp_path):
    """Temporary path for adapter storage."""
    adapter_path = tmp_path / "adapters"
    adapter_path.mkdir(parents=True, exist_ok=True)
    
    # Set environment variable
    original_path = os.getenv("ADAPTER_STORAGE_PATH")
    os.environ["ADAPTER_STORAGE_PATH"] = str(adapter_path)
    
    yield adapter_path
    
    # Restore original
    if original_path:
        os.environ["ADAPTER_STORAGE_PATH"] = original_path
    else:
        os.environ.pop("ADAPTER_STORAGE_PATH", None)
