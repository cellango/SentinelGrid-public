# Model Gateway Test Suite

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


## Overview

Comprehensive test suite for the Model Gateway service, covering:
- Training data management
- LoRA adapter training
- Job queue integration
- Tenant isolation
- End-to-end workflows

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── pytest.ini                     # Pytest configuration
├── test_training_data_service.py  # Training data service tests
├── test_adapter_training_service.py  # Training service tests
├── test_training_api.py           # API endpoint tests
├── test_job_queue.py              # Job queue tests
├── test_e2e_training.py           # End-to-end workflow tests
├── test_git_ingestion_service.py  # Git ingestion service unit tests
├── test_scheduled_ingestion.py    # Scheduled ingestion service tests
├── test_git_ingestion_api.py      # Git ingestion API integration tests
└── test_git_ingestion_e2e.py      # Git ingestion E2E tests
```

## Running Tests

### Prerequisites

1. **Activate conda environment:**
   ```bash
   conda activate SentinelTest
   ```

2. **Install test dependencies:**
   ```bash
   cd backend/services/model_gateway
   pip install -r tests/requirements.txt
   ```

3. **Set environment variables:**
   ```bash
   export TEST_DATABASE_URL=postgresql://sg:sg@localhost:5432/test_sg
   export REDIS_URL=redis://localhost:6379
   export ADAPTER_STORAGE_PATH=/tmp/test_adapters
   ```

### Run All Tests

```bash
cd backend/services/model_gateway
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/ -v -m "not e2e"

# End-to-end tests
pytest tests/ -v -m e2e

# Integration tests
pytest tests/ -v -m integration

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Run Specific Test Files

```bash
# Training data service tests
pytest tests/test_training_data_service.py -v

# API endpoint tests
pytest tests/test_training_api.py -v

# End-to-end tests
pytest tests/test_e2e_training.py -v

# Git ingestion tests
pytest tests/test_git_ingestion_service.py -v      # Unit tests
pytest tests/test_scheduled_ingestion.py -v        # Scheduled polling tests
pytest tests/test_git_ingestion_api.py -v          # API tests
pytest tests/test_git_ingestion_e2e.py -v          # E2E tests
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

## Test Categories

### Unit Tests
- Service layer tests
- Function-level validation
- Mock dependencies
- Fast execution
- **Git Ingestion:** `test_git_ingestion_service.py`, `test_scheduled_ingestion.py`

### Integration Tests
- Service integration
- Database operations
- Redis queue operations
- API endpoint tests
- Requires test database/Redis
- **Git Ingestion:** `test_git_ingestion_api.py`

### End-to-End Tests
- Full workflow tests
- API-to-database flow
- Real service interactions
- Complete user workflows
- May require services running
- **Git Ingestion:** `test_git_ingestion_e2e.py`

## Fixtures

### `db_session`
- Provides test database session
- Creates/drops tables per test
- Isolated test environment

### `test_tenant_id`
- Generates unique tenant ID per test
- Ensures tenant isolation

### `test_training_data`
- Sample training data (10 Q&A pairs)
- Ready for training tests

### `mock_redis`
- Mocks Redis connection
- For tests that don't need real Redis

### `mock_job_queue`
- Mocks RQ job queue
- Allows testing without running workers

### `mock_peft_available`
- Mocks PEFT library availability
- For tests that don't need actual model training

### `mock_model_loading`
- Mocks model loading
- Avoids downloading models during tests

### `client`
- FastAPI test client
- For API endpoint testing

## Mocking Strategy

### Why Mock?
- **Speed:** Avoid downloading multi-GB models
- **Cost:** No GPU required for unit tests
- **Isolation:** Tests don't depend on external resources
- **Reliability:** Tests run consistently

### What's Mocked?
- Model loading (AutoModelForCausalLM, AutoTokenizer)
- Training execution (Trainer.train)
- Redis connection (for unit tests)
- Job queue (for unit tests)

### What's Not Mocked?
- Database operations (use test database)
- API endpoints (FastAPI TestClient)
- Service logic (test actual implementations)

## Test Database

### Option 1: SQLite (Default)
- Fast, in-memory
- No setup required
- Good for unit tests

### Option 2: PostgreSQL
- More realistic
- Better for integration tests
- Requires test database setup

Set `TEST_DATABASE_URL` environment variable to use PostgreSQL.

## Continuous Integration

Tests should run in CI with:
- Test database (PostgreSQL or SQLite)
- Mocked external dependencies
- Fast execution (< 5 minutes)
- High coverage (> 80%)

## Known Limitations

1. **Model Training:** Requires GPU and large models
   - **Solution:** Mocked in unit tests
   - **Alternative:** Integration tests with actual models

2. **Redis Queue:** Requires Redis running
   - **Solution:** Mocked in unit tests
   - **Alternative:** Integration tests with test Redis

3. **pgvector Extension:** Requires PostgreSQL with pgvector
   - **Solution:** Skip vector tests if unavailable
   - **Alternative:** Use test PostgreSQL with pgvector

## Adding New Tests

1. **Unit Tests:** Test individual functions/methods
   - Use mocks for external dependencies
   - Fast execution (< 1 second each)

2. **Integration Tests:** Test service interactions
   - Use real database/Redis
   - May be slower

3. **E2E Tests:** Test full workflows
   - Mark with `@pytest.mark.e2e`
   - May require services running

## Troubleshooting

### Tests Fail with "Redis unavailable"
- Mock Redis in unit tests
- Ensure Redis is running for integration tests

### Tests Fail with "Model not found"
- Mock model loading
- Ensure models are available for integration tests

### Tests Fail with "Database connection error"
- Check `TEST_DATABASE_URL`
- Ensure test database exists
- Verify connection credentials

